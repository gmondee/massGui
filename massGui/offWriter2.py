import shutil
import mass
from mass.off import ChannelGroup, getOffFileListFromOneFile
import sys, codecs, time, os
with open(r'C:\Users\Grant Mondeel\Box\my EUV\tes\realtime\realtime\Data\FakeData\20200107_fake\20200107_run0002_chan1.off','wb') as file:
    pass #clear the fake file
with open(r'C:\Users\Grant Mondeel\Box\my EUV\tes\realtime\realtime\Data\FakeData\Source\20200107\0002\20200107_run0002_chan1.off', 'rb') as f1:
    # fl = getOffFileListFromOneFile(f1, maxChans=1)
    # data = ChannelGroup(fl)             #all of the channels 
    # ds = data[1]

    # state = 'A'
    # stateSlice = ds.statesDict[state]

    """
    for each state:
        write state and timestamp to experiment state file

        ...get time intervals based on size of stateSlice and write the records in chunks...
            recordsInState = ds.offFile[stateSlice]
            write records to new off file?
    
    can we get a direct link between file.read and the off records?
    """


    """
    alternative: write records as it is done below, and read them as they come in. 
    Then, update the states file as the unixnanos time from the most recent ds.offFile record advances.
    
    
    """
    first = True
    """read the experiment state file to get a list of states/ignores and the times that they start"""
    with open(r"C:\Users\Grant Mondeel\Box\my EUV\tes\realtime\realtime\Data\FakeData\20200107_fake\full_states.txt", 'r') as expOld, open(r"C:\Users\Grant Mondeel\Box\my EUV\tes\realtime\realtime\Data\FakeData\20200107_fake\20200107_run0002_experiment_state.txt", 'w') as expNew:
        offFile = getOffFileListFromOneFile(r'C:\Users\Grant Mondeel\Box\my EUV\tes\realtime\realtime\Data\FakeData\Source\20200107\0002\20200107_run0002_chan1.off', maxChans=1)
        dataOld = ChannelGroup(offFile)
        dsOld = dataOld[1]
        times, states = dsOld.experimentStateFile.unixnanos, dsOld.experimentStateFile.allLabels
        Lines = expOld.readlines()
        
        
        while True:
            with open(r'C:\Users\Grant Mondeel\Box\my EUV\tes\realtime\realtime\Data\FakeData\20200107_fake\20200107_run0002_chan1.off','ab') as f2:
                if first:
                    
                    buf=f1.read(8000)   #buffer and some records
                    n=f2.write(buf)
                    expNew.write(Lines[0]) #header info about the file
                    expNew.write(Lines[1]) #first label(state/ignore/start etc) and time
                    expNew.write(Lines[2]) #first label(state/ignore/start etc) and time
                    f2.flush()
                    os.fsync(f2.fileno())
                    first = False
                    
                    sInd = 3
                    offFile2 = getOffFileListFromOneFile(r'C:\Users\Grant Mondeel\Box\my EUV\tes\realtime\realtime\Data\FakeData\20200107_fake\20200107_run0002_chan1.off', maxChans=1)
                    data = ChannelGroup(offFile2)
                    ds = data[1]
                    size = ds.offFile.dtype.itemsize
                    #sInd = 0
                    

                latest = ds.offFile[-1]
                latestTime = latest[3]
                
                buf=f1.read(size*150)   #writes a channel within a few minutes
                if buf: 
                    n=f2.write(buf)
                    f2.flush()
                    os.fsync(f2.fileno())
                    time.sleep(3)
                    if latestTime >= times[sInd]:
                        expNew.write(Lines[sInd])
                        sInd+=1
                """ if latestTime >= nextStateTime:
                        write one line to the experiment state file
                        nextStateTime = next timestamp
                        nextState = next state
                        """