import shutil

# with open(r'C:\Users\Grant Mondeel\Box\my EUV\tes\realtime\realtime\Data\FakeData\Source\20200107\0002\20200107_run0002_chan1.off', 'r', encoding="ANSI") as fileR:
#     with open(r'C:\Users\Grant Mondeel\Box\my EUV\tes\realtime\realtime\Data\FakeData\20200107_fake\20200107_run0002_chan1.off','w') as fileW:
#         #shutil.copy(r"C:\Users\Grant Mondeel\Box\my EUV\tes\realtime\realtime\Data\FakeData\20200107_fake\base.off", fileW)
#         for i, line in enumerate(fileR):
#             print(i)
#             fileW.writelines(line)


with open(r'C:\Users\Grant Mondeel\Box\my EUV\tes\realtime\realtime\Data\FakeData\Source\20200107\0002\20200107_run0002_chan1.off', 'r', encoding="ANSI") as f1:
    with open(r'C:\Users\Grant Mondeel\Box\my EUV\tes\realtime\realtime\Data\FakeData\20200107_fake\20200107_run0002_chan1.off','w') as f2:
       while True:
          buf=f1.read(1024)
          if buf: 
              for byte in buf:
                 pass    # process the bytes if this is what you want
                         # make sure your changes are in buf
              n=f2.write(buf)
          else:
              break
