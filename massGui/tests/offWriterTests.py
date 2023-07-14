import shutil
import mass
from mass.off import ChannelGroup, getOffFileListFromOneFile
import sys, codecs, time, os

"""
for each state:
    write state and timestamp to experiment state file

    ...get time intervals based on size of stateSlice and write the records in chunks...
        recordsInState = ds.offFile[stateSlice]
        write records to new off file?


alternative: write records as it is done below, and read them as they come in. 
Then, update the states file as the unixnanos time from the most recent ds.offFile record advances.
"""
def runOffWriterForTests():
    basedir = os.path.dirname(os.path.abspath(__file__)) #r'C:\\Users\\Grant Mondeel\\Box\\my EUV\\tes\\realtime\\realtime\\Summer2023\\massGui\\massGui\\tests'
    with open(os.path.join(basedir,'DataForTests', '20200107_Realtime', '20200107_run0002_chan1.off'), 'wb'):
        pass #clear the destination file
    with open(os.path.join(basedir,r"DataForTests", "Source", "20200107", "0002", "20200107_run0002_chan1.off"), 'rb') as source_off_file:
        first = True
        """read the experiment state file to get a list of states/ignores and the times that they start"""
        with open(os.path.join(basedir,r'DataForTests', "20200107_Realtime", 'full_states.txt'), 'r') as expSource, open(os.path.join(basedir,r"DataForTests", "20200107_Realtime", "20200107_run0002_experiment_state.txt"), 'w') as expDest:
            offFile = getOffFileListFromOneFile(os.path.join(basedir,r"DataForTests", "Source", "20200107", "0002", "20200107_run0002_chan1.off"), maxChans=2)
            dataOld = ChannelGroup(offFile)
            dsOld = dataOld[1]
            times, states = dsOld.experimentStateFile.unixnanos, dsOld.experimentStateFile.allLabels
            Lines = expSource.readlines()
            
            
            while True:
                with open(os.path.join(basedir, r"DataForTests", "20200107_Realtime", "20200107_run0002_chan1.off"),'ab') as destination_off_file:
                    if first:
                        
                        buf=source_off_file.read(80000)   #buffer and some records
                        n=destination_off_file.write(buf)
                        expDest.write(Lines[0]) #header info about the file
                        expDest.write(Lines[1]) #first label(state/ignore/start etc) and time
                        expDest.write(Lines[2]) #first label(state/ignore/start etc) and time
                        expDest.flush()
                        os.fsync(expDest.fileno())
                        destination_off_file.flush()
                        os.fsync(destination_off_file.fileno())
                        first = False
                        
                        sInd = 3
                        offFile2 = getOffFileListFromOneFile(os.path.join(basedir,r"DataForTests", "20200107_Realtime", "20200107_run0002_chan1.off"), maxChans=1)
                        data = ChannelGroup(offFile2)
                        ds = data[1]
                        size = ds.offFile.dtype.itemsize
                        #sInd = 0
                        
                    data.refreshFromFiles()
                    latest = ds.offFile[-1]
                    latestTime = latest[3]
                    
                    buf=source_off_file.read(size*50)   #writes a channel within a few minutes
                    if buf: 
                        n=destination_off_file.write(buf)
                        destination_off_file.flush()
                        os.fsync(destination_off_file.fileno())
                        time.sleep(0.05)
                        #print("latest time = ",latestTime, "times[sInd] = ", times[sInd])
                        print("The next state is ",states[sInd])
                        if latestTime >= times[sInd]:
                            expDest.write(Lines[sInd])
                            expDest.flush()
                            os.fsync(expDest.fileno())
                            sInd+=1
                    """ if latestTime >= nextStateTime:
                            write one line to the experiment state file
                            nextStateTime = next timestamp
                            nextState = next state
                            """
                    
def main():
    runOffWriterForTests()
if __name__ =="__main__":
    runOffWriterForTests()