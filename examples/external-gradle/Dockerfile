FROM centos:latest

LABEL PROJECT=HelloWorld

###RUNTIME###

RUN JAVA_HOME="/jdk" /gradle/bin/gradle -p "/src" clean build
RUN cp /src/jar/hello.jar /root/
RUN cp -r /jdk/jre /root/

ENV JAVA_HOME /root/jre
ENV PATH /root/jre/bin:$PATH

CMD java -cp /root/hello.jar HelloWorld