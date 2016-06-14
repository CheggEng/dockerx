# dockerx
## Description
**dockerx** is a tool which extends functionality of **docker**. This tool adds following enhancements:
- use volume mounts during build
- point to a custom Docker registry by default
- put build parameters into an options file
- patch existing images using command line instructions
- flatten Docker images
- remove images based on regular expression

**dockerx** extends functionality of **build**, and adds commands **patch** and **flatten**.
If command is not recognized by **dockerx**, it will pass the command with all arguments to regular **docker** tool.
   
## build
**dockerx build** extends functionality of Docker's build process and adds ability to execute runtime instructions. From another side, same _Dockerfile_ will work using regular "docker build".

In the _Dockerfile_, all commands below **###RUNTIME###** comment line will be executed in runtime. It can be useful, for example, if source code is checked out as a part of the build process, and this Docker layer should not be cached.

Also, this command adds Docker's volume mount options _-v_ and _--volume_ to the build process. For example, _"dockerx build **-v ~/.gradle:/gradle** -t chegg/myimage:latest ."_

Docker's option **"&lt; &lt;filename&gt;"** is not currently supported, this script requires a file named **Dockerfile** in the content folder, or **"-f &lt;filename&gt;"** option passed to run.

### How to use?

**dockerx build** supports all command line arguments of regular **docker build** command, excluding **&lt; &lt;filename&gt;**. 

### How it works?

Script parses given **Dockerfile**, and divides it into two separate files:

*   **df.c** - static Dockerfile. Will be executed using regular **"docker build"** command. Image name passed using an option _-t_ or _--tag_ will be replaced with temporary UUID. 
*   **df.sh** - shell script which will be copied into the temporary image. Script name will match the temporary image name. This shell script contains all commands from the Dockerfile below the **###RUNTIME###** line. When build is complete, **dockerx** will start a container based on the temporary image, and execute the shell script. After this, the container will be committed as a Docker image with a name specified in **dockerx build** command line.

### Supported arguments

Script supports all arguments of regular docker build command, and following additional arguments:

*   **-v**, **--volume**: mount an external volume (see **docker run** docs for more details)
*   **--opts-file**: loads command line arguments from a specified file; all arguments can be stored in opts file except path to **Dockerfile**
*   **--registry**: use private registry instead of DockerHub without changing your **Dockerfile**; script will update base image name in **FROM** instruction, and will also apply new registry to the output image name 

### Special cases

Commands **CMD** and  **ENTRYPOINT** from the base imageby default will be overwritten during "docker commit". Because of this, **dockerx ** will duplicate these commands in commit instructions. If **CMD** or **ENTRYPOINT** is not specified in the **Dockerfile**, **dockerx** will inspect the base image to get these values.

Command **ADD** will be automatically moved to the static **Dockerfile**. To add files or folders from mounted volumes during runtime, use **"RUN cp ..."** instead. 

If command **USER** switches user profile in the image, there is no way to return back to **root** profile in the runtime without entering sudo password. In this case, **dockerx** will analyze the static part of **Dockerfile**, will restore **root** session, and let the shell script know about another user profile.

Command **ENV** will be executed in the shell script as **"export"** command, and also it wil be added to **"docker commit"** command instructions.

### Custom Dockerfile instructions

Command **dockerx build** supports custom commands in Dockerfile. These commands must start with #! to be detected.

For example:

`#!TAG my-image:latest`

Implementation of these commands can be found in the **utils/extras.py** file. Custom commands can be extended by adding new functions with **@docker** annotation in **utils/extras.py** file. Function must have following format:

<pre><span>@</span><span>docker</span> <span>def</span> <span>mycommand</span>(<span>params</span>, context)<span>:
</span> <span>#Some code here</span></pre>

Command will receive all arguments, and a context map which will contain image name and ID. 

There is no need to register this command somewhere, it will be detected using **@docker** annotation. Command name in **Dockerfile** will match the function name in uppercase. In given example it will be 

`#!MYCOMMAND some parameters`

Commands will be executed with their natural order. Methods can append context map to share data with other commands. 
   
   
   
## patch
**dockerx patch** patches an existing image using **Dockerfile** instructions as command line arguments. It supports all arguments of **dockerx build**, and allows to pass multiple command instructions. Usage:
<pre>dockerx patch --command '&lt;DOCKER-INSTRUCTION&gt;' [--command '&lt;DOCKER-INSTRUCTION&gt;'...] &lt;IMAGE_NAME&gt;</pre>

### How it works?
**dockerx** will create a temporary folder, and save given instructions as a **Dockerfile**. It will ignore **FROM** instructions passed, and will use **&lt;IMAGE_NAME&gt;** as **FROM** as well as an output image name.
After creating a **Dockerfile**, script will internally call **dockerx build**, and pass all arguments excluding _--command_.
   
   
   
## flatten
**dockerx flatten** reduces size of Docker images. Usage:
<pre>dockerx flatten &lt;IMAGE_NAME&gt; [&lt;TARGET_IMAGE_NAME&gt;]</pre>
### How it works?
**dockerx** will inspect the source image, and extract the metadata. Then **dockerx** will start a new container based on the source image, export it using **docker export**, re-import it back as a target image. If target image name is not provided, **dockerx** will overwrite the source image. While importing, **dockerx** will apply the saved metadata.


## rmi
**dockerx rmi** removes images based on a regex mask and exclude list. Usage:
<pre>dockerx [-x &lt;EXCLUDED_IMAGE_NAME&gt;] &lt;IMAGE_NAME_MASK&gt;</pre>
Example:
<pre>dockerx rmi -x my-project:latest my-project:.*</pre>
It supports all regular options of **docker rmi**. 
### How it works?
**dockerx** will list all images, find matching names, exclude specified images, and will remove the rest. 