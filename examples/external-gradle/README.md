# HelloWorld

This example project builds a Java project using mounted external JDK and Gradle, installs JRE and configures Docker image to run the HelloWorld.class as a default command.
   
This build requires following pre-requisites:
- Create a folder **docker-mount** in your home directory.
- Download and unpack JDK archive into **docker-mount** folder: <pre>wget --no-cookies --no-check-certificate --header "Cookie: gpw_e24=http%3A%2F%2Fwww.oracle.com%2F; oraclelicense=accept-securebackup-cookie" "http://download.oracle.com/otn-pub/java/jdk/7u79-b15/jdk-7u79-linux-x64.tar.gz"</pre>
- Download and unpack Gradle archive into **docker-mount** folder: <pre>wget https://services.gradle.org/distributions/gradle-2.13-bin.zip</pre>
    
    
Now switch back to **dockerx/examples/external-gradle** folder and run following build command:
<pre>../../dockerx build --opts-file=build.opts -t hello-world:latest .</pre>
    
## Inside build.opts
Let's walk the options file **build.opts**:
<pre>-v ~/docker-mount/jdk1.7.0_79:/jdk</pre>
_Mount external Jdk folder as **/jdk** path inside Docker container_
<pre>-v ~/docker-mount/gradle:/gradle</pre>
_Mount external Gradle folder as **/gradle** path inside Docker container_
<pre>-v ./hello:/src</pre>
_Mount project folder as **/src** path inside Docker container_
<pre>-m 256m</pre>
_Request Docker to allocate 256 Mb of memory for image build process_
    
##Inside Dockerfile
Let's take a look at **Dockerfile**.
<pre>FROM centos:latest</pre>
_Declare that this Docker image is based on **centos** image_
<pre>LABEL PROJECT=HelloWorld</pre>
_Add an informational label **PROJECT** to Docker image descriptor_
<pre>&#35;&#35;&#35;RUNTIME&#35;&#35;&#35;</pre>
_This line shows that all instructions below should be executed as runtime commands_
<pre>RUN JAVA_HOME="/jdk" /gradle/bin/gradle -p "/src" clean build</pre>
_Run **gradle build** on mounted Java project folder using external Gradle binary. This line also makes Gradle use external JDK path as **JAVA_HOME**_
<pre>RUN cp /src/jar/hello.jar /root/</pre>
_Since **gradle build** creates a JAR in the external **/src/jar** folder, copy the JAR file into Docker image's internal file system_
<pre>RUN cp -r /jdk/jre /root/</pre>
_JDK folder contains **jre** folder inside. Copy it into Docker image's internal file system. There is no need to copy the whole JDK folder, since in runtime we need only JRE_  
<pre>ENV JAVA_HOME /root/jre
ENV PATH /root/jre/bin:$PATH</pre>
_Export **&#36;JAVA_HOME** environment variable, also add Java binaries folder to **&#36;PATH**_
<pre>CMD java -cp /root/hello.jar HelloWorld</pre>
_Execute **HelloWorld.class** when running the image_
   
##Running the image
To run the image, simply execute following:
<pre>docker run hello-world</pre>
Since **dockerx** passes all commands to Docker, following command is identical to the one above:
<pre>dockerx run hello-world</pre>
   
##Optimize it!
There are many ways to optimize the build process. This simple project doesn't have any dependencies, but if you have a large Java application which uses many third-party tools, Gradle will download all artifacts on every Docker image build, since it will start from a blank **centos** image with no library cache.
    
So, let's re-use the cache. Create an empty directory **cache** in your **docker-mount** directory. Now add following line to **build.opts** file:
<pre>-v ~/docker-mount/cache:/root/.gradle</pre>
Done. Now Gradle will store it's cache in external mount, and will re-use it every time you run **dockerx build**.
