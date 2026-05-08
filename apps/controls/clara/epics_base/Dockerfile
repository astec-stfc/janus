##########################################################
# MASTER CONTAINER TO USE AS A BASE FOR OTHER CONTAINERS #
#														 #
# Installs and makes: 									 # 
#		Centos7, Epics, synApps and VA	Modules          #
##########################################################

##########################################################
# Centos7								 

FROM centos:7 AS epics_base

# update mirror registry to base-repo as centos7 is EOL
RUN sed -i s/mirror.centos.org/vault.centos.org/g /etc/yum.repos.d/*.repo
RUN sed -i s/^#.*baseurl=http/baseurl=http/g /etc/yum.repos.d/*.repo
RUN sed -i s/^mirrorlist=http/#mirrorlist=http/g /etc/yum.repos.d/*.repo

# Yum
RUN yum -y groupinstall 'Development Tools' 
RUN yum -y install readline-devel 
RUN yum -y install epel-release 
RUN yum -y install re2c 
RUN yum -y install wget 
RUN yum -y install vim 
RUN yum -y install python3 
RUN pip3 install pyepics
 
##########################################################
# Epics
#ARG  OS=base_centos_7:latest
#FROM ${OS}

# Define home and architecture
ARG VA_BASE=/BUILD_VA/
ARG VA_ARCH=linux-x86_64
ENV VA_BASE=$VA_BASE
ENV VA_ARCH=$VA_ARCH
WORKDIR $VA_BASE

WORKDIR $VA_BASE 
RUN git clone --recursive --branch=7.0 https://github.com/epics-base/epics-base.git ./va/epics-base
# Make EPICS
RUN cd ./va/epics-base; make   


##########################################################
# synApps
COPY . .
RUN git clone https://github.com/EPICS-synApps/support.git
RUN chmod a+x assemble_synApps.sh
RUN ./assemble_synApps.sh

RUN cd synApps/support ; make clean ; make release

#RUN git clone https://CSSI74:glpat-hTTL_7DdRVsYXk4R4nWe@gitlab.stfc.ac.uk/CSSI/EPICS/Support/seq.git                              
#RUN cd seq; make clean; make release             

# Follow the tectalk advice and don't use environment variables, use make include instead
WORKDIR $VA_BASE

COPY RELEASE.local  ./va/RELEASE.local

RUN sed -i 's|$VA_ARCH|'$VA_ARCH'|g; s|$VA_BASE|'$VA_BASE'|g;' ./va/RELEASE.local

# Set up EPICS environment arrays for runtime
ENV PATH=$VA_BASE/va/epics-base/bin/$VA_ARCH:$PATH
ENV EPICS_CA_MAX_ARRAY_BYTES=100000000
ENV EPICS_CAS_SERVER_PORT=6000
ENV EPICS_CA_SERVER_PORT=6000
ENV EPICS_CA_AUTO_ADDR_LIST=NO
ENV EPICS_CA_ADDR_LIST=localhost
ENV EPICS_PVA_SERVER_PORT=6092
ENV EPICS_PVAS_SERVER_PORT=6092
ENV EPICS_PVA_AUTO_ADDR_LIST=NO
ENV EPICS_PVA_ADDR_LIST=""
ENV EPICS_PVAS_INTF_ADDR_LIST=0.0.0.0
