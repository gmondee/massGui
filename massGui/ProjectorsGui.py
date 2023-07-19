from PyQt6 import QtWidgets
import PyQt6
import PyQt6.uic
import os
import mass
import sys
import traceback
import h5py
import gc
import matplotlib.pyplot as plt
from mass.core.projectors_script import make_projectors
from .canvas import MplCanvas



def show_popup(parent, text, traceback=None, icon=QtWidgets.QMessageBox.Icon.Warning):
        msg = QtWidgets.QMessageBox(text=text, parent=parent)
        msg.setWindowTitle("Error")
        msg.setIcon(icon)
        if traceback is not None:
            msg.setDetailedText(traceback)
        ret = msg.exec()



class projectorsGui(QtWidgets.QDialog):  #handles linefit function call. lets user choose line, states, channel
    def __init__(self, parent=None):
        super(projectorsGui, self).__init__(parent)
        QtWidgets.QDialog.__init__(self)
        self.args = ArgsDict()
        self.setParams()
    def setParams(self):
        self.args.pulse_path = None
        self.args.noise_path = None
        self.build()
        self.connect()

    def build(self):
        PyQt6.uic.loadUi(os.path.join(os.path.dirname(__file__), "ui","ProjectorsGui.ui"), self) #,  s, attr, state_labels, colors)
    def connect(self):
        self.pulsePathButton.clicked.connect(self.openPulseFile)
        self.noisePathButton.clicked.connect(self.openNoiseFile)
        self.startButton.clicked.connect(self.handle_make_projectors)
        self.plotProjectorsButton.clicked.connect(self.plotProjectors)
        
    def openPulseFile(self):
        self.args.pulse_path = self.handle_choose_file(lookingForThis='pulses')
        if self.args.pulse_path is not None:
            self.pulsePathLineEdit.setText(self.args.pulse_path)

    def openNoiseFile(self):
        self.args.noise_path = self.handle_choose_file(lookingForThis='noise records')
        if self.args.noise_path is not None:
            self.noisePathLineEdit.setText(self.args.noise_path)

    def handle_make_projectors(self):
        self.args.silent = False
        if self.args.pulse_path is None:
            return
            #popup, need to set this path first
        #self.args.pulse_path is set by the file dialog
        if self.args.noise_path is None:
            return
            #popup, need to set this path first
        #self.args.pulse_path is set by the file dialog
        self.args.max_channels = int(self.maxChansBox.value())
        outputPath = self.outputFileNameBox.text()
        if outputPath.strip(' ') == '':
            self.args.output_path = None
        elif outputPath.endswith('.hdf5'):
            self.args.output_path = outputPath
        else:
            self.args.output_path = outputPath+'.hdf5'
        self.args.replace_output = self.replaceCheckbox.isChecked()
        self.args.n_sigma_pt_rms = self.sigmaPtRmsBox.value()
        self.args.n_sigma_max_deriv = self.sigmaMaxDerivBox.value()
        self.args.n_basis = int(self.nprojectorsBox.value())
        self.args.maximum_n_pulses = int(self.maxPulsesBox.value())
        self.args.mass_hdf5_path = None
        self.args.mass_hdf5_noise_path = None
        self.args.invert_data = self.invertDataCheckbox.isChecked()
        self.args.dont_optimize_dp_dt = self.dontOptimiseCheckbox.isChecked()
        self.args.extra_n_basis_5lag = int(self.extraBasis5lagBox.value())
        f_ats = self.cutoffATSBox.value()
        if f_ats == 0:
            self.args.f_3db_ats = None
        else:
            self.args.f_3db_ats = f_ats
        f_5lag = self.cutoff5lagBox.value()
        if f_5lag == 0:
            self.args.f_3db_5lag = None
        else:
            self.args.f_3db_5lag = f_5lag
        self.args.noise_weight_basis = self.noiseWeightingCheckbox.isChecked()
        try:
            #main(self.args)
            channums = mass.ljh_util.ljh_get_channels_both(self.args.pulse_path, self.args.noise_path)
            print("found these {} channels with both pulse and noise files: {}".format(len(channums), channums))
            nchan = len(channums)
            if self.args.max_channels < nchan:
                channums = channums[:self.args.max_channels]
                print("chose first max_channels={} channels".format(self.args.max_channels))
            if len(channums) == 0:
                raise Exception("no channels found for files matching {} and {}".format(
                    self.args.pulse_path, self.args.noise_path))
            pulse_basename, _ = mass.ljh_util.ljh_basename_channum(self.args.pulse_path)
            noise_basename, _ = mass.ljh_util.ljh_basename_channum(self.args.noise_path)
            pulse_files = [pulse_basename+"_chan{}.ljh".format(channum) for channum in channums]
            noise_files = [noise_basename+"_chan{}.ljh".format(channum) for channum in channums]
            # handle output filename
            if self.args.output_path is None:
                self.args.output_path = os.path.normpath(pulse_basename+"_model.hdf5")
            else:
                self.args.output_path = os.path.normpath(os.path.join(os.path.dirname(self.args.pulse_path),self.args.output_path))
            # handle replace_output
            if os.path.isfile(self.args.output_path) and not self.args.replace_output:
                print("output: {} already exists, check the \"Replace existing output files\" box to overwrite".format(self.args.output_path))
                print("aborting")
                show_popup(self, "output: {} already exists, check the \"Replace existing output files\" box to overwrite".format(self.args.output_path))
                return
            # create output file
            with h5py.File(self.args.output_path, "w") as h5:
                n_good, n = make_projectors(pulse_files=pulse_files, noise_files=noise_files, h5=h5,
                                            n_sigma_pt_rms=self.args.n_sigma_pt_rms, n_sigma_max_deriv=self.args.n_sigma_max_deriv,
                                            n_basis=self.args.n_basis, maximum_n_pulses=self.args.maximum_n_pulses, mass_hdf5_path=self.args.mass_hdf5_path,
                                            mass_hdf5_noise_path=self.args.mass_hdf5_noise_path,
                                            invert_data=self.args.invert_data, optimize_dp_dt=not self.args.dont_optimize_dp_dt,
                                            extra_n_basis_5lag=self.args.extra_n_basis_5lag,
                                            f_3db_ats=self.args.f_3db_ats, f_3db_5lag=self.args.f_3db_5lag, noise_weight_basis=True)
                h5.close()
                if n_good == 0:
                    show_popup(self, text=f"all channels bad, could be because you need -i for inverted pulses")
                    print(f"all channels bad, could be because you need -i for inverted pulses")
                    return
            show_popup(self, f"made projectors for {n_good} of {n} channels.\n Written to {self.args.output_path}", icon=QtWidgets.QMessageBox.Icon.Information)
            print(f"made projectors for {n_good} of {n} channels")
            print(f"written to {self.args.output_path}")
            #these three lines are needed to close out of the "byproduct" hdf5 files
            #specifically, in line 185 of channel_group: self.hdf5_file = h5py.File(hdf5_filename, 'w') #is never closed
            del n
            del n_good
            gc.collect()
            with h5py.File(self.args.output_path, "r") as h5:
                self.models = {int(ch) : mass.pulse_model.PulseModel.fromHDF5(h5[ch]) for ch in h5.keys()}
                self.channels = [int(ch) for ch in h5.keys()]
                for ch in self.channels:
                    self.channelBox.addItem("{}".format(ch))
                self.plotProjectorsGroup.setEnabled(True)
        except Exception as exc:
            print("Failed to make projectors!")
            print(traceback.format_exc())
            show_popup(self, "Failed to make projectors!", traceback=traceback.format_exc())

    def plotProjectors(self):      
        channum = int(self.channelBox.currentText())
        self.canvas1 = MplCanvasPlot()
        fig1 = plt.get_fignums()[-1]#canvas1.canvas.fig
        self.canvas2 = MplCanvasPlot()
        fig2 = plt.get_fignums()[-1]#canvas2.canvas.fig
        #fig1 = plt.figure()
        #canvas1 = MplCanvas(fig1.number)
        #fig2 = plt.figure()
        #canvas2 = MplCanvas(fig2.number)
        self.models[channum].plot(fig1, fig2)
        self.canvas1.show()
        self.canvas2.show()

    def ljh2off(self):
# parser.add_argument(
#     "ljh_path", help="path a a single ljh file, other channel numbers will be found automatically")
        self.args.output_dir = self.offOutputLineEdit.text()
        if self.args.output_dir == '':
            self.args.output_dir = os.path.dirname(self.args.pulse_path)
        elif not os.path.isdir(self.args.output_dir):
            os.mkdir(self.args.output_dir)
        elif not self.args.replace_output:
            print("dir {} exists, check the \"Replace existing output files\" box to overwrite".format(self.args.output_dir))
            show_popup(self, "dir {} exists, check the \"Replace existing output files\" box to overwrite".format(self.args.output_dir))
            return
# parser.add_argument("h5_path", help="path to a hdf5 file with projectors and bases")
# parser.add_argument(
#     "output_dir", help="path to output dir (will be created if it doesn't exist)")
# parser.add_argument("-r", "--replace_output",
#                     help="pass this to overwrite off files with the same path", action="store_true")
# parser.add_argument("-m", "--max_channels",
#                     help="stop after processing this many channels", default=2**31, type=int)
# parser.add_argument("--n_ignore_presamples",
#                     help="ignore this many presample before the rising edge when calculating pretrigger_mean", default=0, type=int)


        ljh_filenames, off_filenames = mass.ljh2off.ljh2off_loop(
            self.args.ljh_path, self.args.h5_path, self.args.output_dir, self.args.max_channels, self.args.n_ignore_presamples)
        print("full path to first off file:")
        print(os.path.abspath(off_filenames[0]))

    def handle_choose_file(self, lookingForThis):
        #options = QFileDialog.options(QFileDialog)
        if not hasattr(self, "_choose_file_lastdir"):
            dir = os.path.expanduser("~")
        else:
            dir = self._choose_file_lastdir
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, f"Select an ljh file with {lookingForThis}", dir,
            "ljh Files (*.ljh);;All Files (*)")#, options=options)
        if fileName:
            self._choose_file_lastdir = os.path.dirname(fileName)
            return fileName
            #self.load_file(fileName)

        

class MplCanvasPlot(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(MplCanvasPlot, self).__init__(parent)
        QtWidgets.QDialog.__init__(self)
        self.setParams()
    def setParams(self):
        self.build()
        self.connect()

    def build(self):
        PyQt6.uic.loadUi(os.path.join(os.path.dirname(__file__), "ui","mplCanvasPlot.ui"), self)
    def connect(self):
        ...



class ArgsDict(): #used like a dictionary for the arguments
    pass
    
def main():
    app = QtWidgets.QApplication(sys.argv)
    pg = projectorsGui()
    pg.show()
    app.exec()

if __name__ == '__main__':
    main()