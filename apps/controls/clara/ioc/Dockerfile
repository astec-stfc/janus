##########################################################
# IOC BOOT CONTAINER									 #
#														 #
#     Installs and makes ProcServ					     # 
#     Launches IOC          							 #
##########################################################

#FROM epics_base AS ioc
# cssi-repository.dl.ac.uk:1442/repository/docker_store/epics:latest
FROM epics_base  
COPY . .

##########################################################
# Clone Modules
RUN git clone https://ujo48515:glpat-TaqZcrGgE5RKxMSiY1ek@gitlab.stfc.ac.uk/CSSI/EPICS/Support/interface_magnets.git ./va/interface_magnets    
RUN git clone https://ujo48515:glpat-TaqZcrGgE5RKxMSiY1ek@gitlab.stfc.ac.uk/CSSI/EPICS/Support/interface_screens.git ./va/interface_screens    
RUN git clone --branch add_twiss_tables https://ujo48515:glpat-TaqZcrGgE5RKxMSiY1ek@gitlab.stfc.ac.uk/CSSI/EPICS/Support/interface_CLARA_VELA_Simulation.git ./va/interface_CLARA_VELA 
RUN git clone --branch VA https://ujo48515:glpat-TaqZcrGgE5RKxMSiY1ek@gitlab.stfc.ac.uk/CSSI/EPICS/Support/engineeringunitconverter.git ./va/magnets_converter
RUN git clone --branch add_twiss_tables https://ujo48515:glpat-TaqZcrGgE5RKxMSiY1ek@gitlab.stfc.ac.uk/CSSI/CLARA/IOC/VirtualAcceleratorIOC.git ./va/CLARA_VELA_ioc      
#RUN git clone http://www-csr.bessy.de/control/SoftDist/sequencer/repo/branch-2-2.git       ./va/seq    

###################
# Install and Make support modules
RUN cd ./va/interface_magnets    ; make clean; make
#RUN cd ./va/interface_screens    ; make clean; make
RUN cd ./va/interface_CLARA_VELA ; make clean; make
RUN cd ./va/magnets_converter    ; make clean; make
RUN cd ./va/CLARA_VELA_ioc       ; make clean; make

RUN cp  ./va/interface_screens/interfaceApp/Db/*txt ./va/CLARA_VELA_ioc/iocBoot/vaioc/
RUN	chmod a+x ./va/CLARA_VELA_ioc/iocBoot/vaioc/st.cmd

###################
# Install and Make# ProcServ      
RUN git clone https://github.com/ralphlange/procServ.git ./run
RUN cd ./run; make ; ./configure --disable-doc; make;

###################
# Run Ioc
###################
WORKDIR $VA_BASE/va/CLARA_VELA_ioc/iocBoot/vaioc
RUN chmod a+x ./st.cmd

# Try without proc
#CMD ../../../../run/procServ  -n IOC  -i ^D^C -L ../../../CLARA_VELA_ioc/logfile.txt 6001 ./st.cmd ;\
#    watch 'ps -elf | grep procServ'

# Proc removed for a test as docker attach may do the same thing
CMD ./st.cmd
