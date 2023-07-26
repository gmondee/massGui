Installation: 
If you want an editable installation (recommended), first navigate to the directory where you want to place the files for massGui using Powershell. Then, launch Python and type:

`pip install -e git+https://github.com/gmondee/massGui.git#egg=massGui` 

If you do not want an editable installation, you can use: 

`pip install git+https://github.com/gmondee/massGui.git` 

and it should appear with the rest of your installed packages. 

To get PyQt to work with matplotlib, you might need to run ```pip install matplotlib --upgrade``` after installing massGui.

On Ubuntu, you may have to run this command as well:

```sudo apt-get install libxcb*```

Once massGui is installed, you can run the GUI anywhere by running `massGui` in the terminal. 

This also includes a GUI to make projectors from .ljh files. Either click on the projectors gui button from massGui or launch it directly by running 'projectorsGui' from the terminal.
