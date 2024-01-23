Installation: 
If you want an editable installation (recommended), first navigate to the directory where you want to place the files for massGui using Powershell. Then, launch Python and type:

`pip install -e git+https://github.com/gmondee/massGui.git#egg=massGui` 

If you do not want an editable installation, you can use: 

`pip install git+https://github.com/gmondee/massGui.git` 

and it should appear with the rest of your installed packages. 

This GUI works with Mass version 0.8.1. You can install it like massGui (see above) with ```pip install -e git+https://bitbucket.org/joe_fowler/mass.git@640211d2e497d4c57bb1c0586a995161c66b0202#egg=mass```.

To get PyQt to work with matplotlib, you might need to run ```pip install matplotlib --upgrade``` after installing massGui.

On Ubuntu, you may have to run this command as well:

```sudo apt-get install libxcb*```

Once massGui is installed, you can run the GUI anywhere by running `massGui` in the terminal. 

This also includes a GUI to make projectors from .ljh files. Either click on the projectors gui button from massGui or launch it directly by running `projectorsGui` from the terminal.

[Overview video](https://drive.google.com/file/d/1H3M8ON5Ni1A7ef0eLiWU-HRj-oOciqp7/preview)
