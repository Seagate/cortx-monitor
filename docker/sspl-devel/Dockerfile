ARG  CENTOS_RELEASE=latest
FROM registry.gitlab.mero.colo.seagate.com/centos:${CENTOS_RELEASE}

COPY sspl-uploads.repo /etc/yum.repos.d/
COPY *.spec ./

RUN yum install -y yum-priorities

RUN yum-builddep -y --define 'version 0' libsspl_sec.spec \
    && yum-builddep -y --define 'version 0' sspl-ll.spec \
    && yum-builddep -y --define 'version 0' sspl-test.spec \
    && rm -f *.spec
