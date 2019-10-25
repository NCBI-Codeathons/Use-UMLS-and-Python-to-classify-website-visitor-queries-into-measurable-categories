FROM openjdk:8-jre
  
ENV TINI_VERSION v0.18.0
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /tini
RUN chmod +x /tini
ENTRYPOINT ["/tini", "--"]

WORKDIR /opt/app

COPY . /opt/app

CMD ["java", "-jar", "metamap_worker.jar"]
