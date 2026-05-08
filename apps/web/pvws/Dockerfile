# Build PVWS from source - based on official PVWS docker setup:
# https://github.com/ornl-epics/pvws/blob/main/docker/Dockerfile

FROM alpine/git:latest AS source_fetch
RUN git clone https://github.com/ornl-epics/pvws.git /pvws
RUN cd /pvws && git checkout main

FROM maven:3.8.7-eclipse-temurin-17 AS maven_builder
COPY --from=source_fetch /pvws /pvws
RUN cd /pvws && mvn clean package

FROM tomcat:9.0-jdk17
COPY --from=maven_builder /pvws/target/pvws.war ${CATALINA_HOME}/webapps/
