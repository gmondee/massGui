import shutil
import sys, codecs, time, os
with open(r'C:\Users\Grant Mondeel\Box\my EUV\tes\realtime\realtime\Data\FakeData\20200107_fake\20200107_run0002_chan1.off','wb') as file:
    pass
with open(r'C:\Users\Grant Mondeel\Box\my EUV\tes\realtime\realtime\Data\FakeData\Source\20200107\0002\20200107_run0002_chan1.off', 'rb') as f1:
    while True:
        with open(r'C:\Users\Grant Mondeel\Box\my EUV\tes\realtime\realtime\Data\FakeData\20200107_fake\20200107_run0002_chan1.off','ab') as f2:
            buf=f1.read(440*3*50)   #writes a channel in a few minutes
            if buf: 
                for byte in buf:
                    pass    # process the bytes if this is what you want
                            # make sure your changes are in buf
                n=f2.write(buf)
                f2.flush()
                os.fsync(f2.fileno())
                time.sleep(3)