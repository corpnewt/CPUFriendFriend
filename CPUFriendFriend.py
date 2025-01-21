#!/usr/bin/env python
import os, sys, plistlib, zipfile, tempfile, binascii, shutil
from Scripts import *

class CPUFF:
    def __init__(self):
        self.u = utils.Utils("CPUFriendFriend")
        self.dl = downloader.Downloader()
        self.r = run.Run()
        self.scripts = os.path.join(os.path.dirname(os.path.realpath(__file__)),"Scripts")
        self.out     = os.path.join(os.path.dirname(os.path.realpath(__file__)),"Results")
        self.processor = self.r.run({"args":['/usr/sbin/sysctl', "-n", "machdep.cpu.brand_string"]})[0].strip()
        self.plist = None
        self.plist_data = None
        self.rc_url = "https://raw.githubusercontent.com/acidanthera/CPUFriend/master/Tools/ResourceConverter.sh"
        self.iasl_url = "https://raw.githubusercontent.com/acidanthera/MaciASL/master/Dist/iasl-stable"
        self.iasl = self.check_iasl()
        self.freq_path = "/System/Library/Extensions/IOPlatformPluginFamily.kext/Contents/PlugIns/X86PlatformPlugin.kext/Contents/Resources"
        self.has_epp  = False
        self.epp_find = "6570700000000000000000000000000000000000"
        self.has_perfbias = False
        self.perfbias_find = "706572662D626961730000000000000000000000"
        self.board = self._get_current_board()
        self.smbios = self._get_current_smbios()
        self.rc_path = self._check_rc(self.rc_url)
        self.mylfm = None
        self.myepp = None
        self.myperfbias = None

    def check_iasl(self,try_downloading=True):
        targets = (
            os.path.join(self.scripts, "iasl-dev"),
            os.path.join(self.scripts, "iasl-stable"),
            os.path.join(self.scripts, "iasl-legacy"),
            os.path.join(self.scripts, "iasl")
        )
        target = next((t for t in targets if os.path.exists(t)),None)
        if target or not try_downloading:
            # Either found it - or we didn't, and have already tried downloading
            return target
        # Need to download
        temp = tempfile.mkdtemp()
        try:
            self._download_and_extract(temp,self.iasl_url)
        except Exception as e:
            print("An error occurred :(\n - {}".format(e))
        shutil.rmtree(temp, ignore_errors=True)
        # Check again after downloading
        return self.check_iasl(try_downloading=False)

    def _download_and_extract(self, temp, url):
        ztemp = tempfile.mkdtemp(dir=temp)
        zfile = os.path.basename(url)
        print("Downloading {}".format(os.path.basename(url)))
        self.dl.stream_to_file(url, os.path.join(ztemp,zfile), False)
        search_dir = ztemp
        if zfile.lower().endswith(".zip"):
            print(" - Extracting")
            search_dir = tempfile.mkdtemp(dir=temp)
            # Extract with built-in tools \o/
            with zipfile.ZipFile(os.path.join(ztemp,zfile)) as z:
                z.extractall(search_dir)
        for x in os.listdir(search_dir):
            if x.lower().startswith(("iasl","acpidump")):
                # Found one
                print(" - Found {}".format(x))
                print("   - Chmod +x")
                self.r.run({"args":["chmod","+x",os.path.join(search_dir,x)]})
                print("   - Copying to {} directory".format(os.path.basename(self.scripts)))
                shutil.copy(os.path.join(search_dir,x), os.path.join(self.scripts,x))

    def _get_rc(self, url):
        self.u.head("Downloading ResourceConverter")
        print("")
        target = os.path.join(self.scripts,os.path.basename(url))
        print("Downloading {} from:\n{}".format(os.path.basename(url),url))
        return self.dl.stream_to_file(url, target)

    def _check_rc(self, url):
        target = os.path.join(self.scripts,os.path.basename(url))
        if os.path.exists(target):
            return target
        return self._get_rc(url)

    def _decode(self, var):
        if sys.version_info >= (3,0) and isinstance(var, bytes):
            var = var.decode("utf-8","ignore")
        return var

    def _get_value(self,value):
        out = self._decode(self.r.run({"args":["ioreg","-p","IODeviceTree","-d","2","-k",value]})[0])
        v = "Unknown"
        try:
            v = out.split('{}" = '.format(value))[1].split('<"')[1].split('">')[0]
        except:
            pass
        return v

    def _get_current_board(self):
        return self._get_value("board-id")

    def _get_current_smbios(self):
        return self._get_value("product-name")

    def _get_epp_desc(self,epp):
        epp_int = epp if isinstance(epp,int) else int(epp,16)
        epp_desc = "Unknown"
        if epp_int < 64:
            epp_desc = "Performance"
        elif epp_int < 128:
            epp_desc = "Balanced Performance"
        elif epp_int < 192:
            epp_desc = "Balanced Power Savings"
        else:
            epp_desc = "Maximize Power Savings"
        return epp_desc

    def _get_freq_info(self,x):
        freq = epp = perfbias = None
        data = plist.extract_data(x)
        str_data = self._decode(binascii.hexlify(data)).upper()
        freq = str_data[8:10]
        if self.epp_find in str_data:
            epp = str_data.split(self.epp_find)[1][:2]

        if self.perfbias_find in str_data:
            perfbias = str_data.split(self.perfbias_find)[1][:2]
        return (freq,epp,perfbias)

    def _display_desc(self,desc):
        self.u.head()
        print("")
        if self.mylfm is None:
            print("Current CPU:    {}".format(self.processor))
            print("Current Board:  {}".format(self.board))
            print("Current SMBIOS: {}".format(self.smbios))
            print("")
            for i,x in enumerate(desc):
                print(" {}. {}00MHz --> {}00MHz".format(i+1,int(x["start_freq"],16),int(x["end_freq"],16)))
                if "start_epp" in x:
                    print("  -->{} ({}) --> {} ({})".format(
                        x["start_epp"],
                        self._get_epp_desc(x["start_epp"]),
                        x["end_epp"],
                        self._get_epp_desc(x["end_epp"])
                        ))
                if len(desc):
                    print("")
        else:
            print("Building CPUFriendDataProvider.")

    def main(self):
        if self.board.lower() == "unknown":
            self.u.head("CPUFriendFriend")
            print("")
            print("Couldn't determine board id!")
            print("Aborting!\n")
            exit(1)
        if not self.plist:
            self.plist = os.path.join(self.freq_path,self.board+".plist")
            try:
                with open(self.plist,"rb") as f:
                    self.plist_data = plist.load(f)
            except Exception as e:
                if self.mylfm is None:
                    self.u.head("CPUFriendFriend")
                    print("")
                    print("Could not load {}!\nAborting!\n".format(self.board+".plist"))
                    print(e)
                    print("")
                    exit(1)
        if self.plist_data.get("IOPlatformPowerProfile",{}).get("FrequencyVectors",None) == None:
            self.u.head("CPUFriendFriend")
            print("")
            print("FrequencyVectors not found in {}!\nAborting!\n".format(self.board+".plist"))
            exit(1)
        new_freq = []
        new_desc = []
        total = len(self.plist_data.get("IOPlatformPowerProfile",{}).get("FrequencyVectors",[]))
        for i,x in enumerate(self.plist_data.get("IOPlatformPowerProfile",{}).get("FrequencyVectors",[])):
            freq,epp,perfbias = self._get_freq_info(x)
            data = plist.extract_data(x)
            str_data = self._decode(binascii.hexlify(data)).upper()
            curr_desc = {"start_freq":freq}
            while True:
                self._display_desc(new_desc)
                if self.mylfm is None:
                    # Display the hex, ask for a new value
                    print("Low Frequency Mode (LFM):\n")
                    print("This is the lowest frequency-voltage operating point for your processor. Refer to Intel's ARK site for your processor's LFM setting. If no LFM is defined for your processor, use the default.")
                    print("\nFrequency   :   Hex Value")
                    print("  800MHz      :     0x08")
                    print("  900MHz      :     0x09")
                    print("  1000MHz     :     0x0A")
                    print("  1100MHz     :     0x0B")
                    print("  1200MHz     :     0x0C")
                    print("  1300MHz     :     0x0D")
                    print("\nDefault Setting:    {} ({}00 MHz)\n".format(freq,int(freq,16)))
                    new = self.u.grab("Enter the value for your CPU:  ").upper()
                    if not len(new): new = freq
                    elif new == "Q": self.u.custom_quit()
                    self.mylfm = new
                else:
                    new = self.mylfm
                new = new.replace("0X","")
                new = "".join([x for x in new if x in "0123456789ABCDEF"])
                if len(new) != 2:
                    continue
                # Save the changes
                str_data = str_data[:8]+new+str_data[10:]
                curr_desc["end_freq"] = new
                break
            if epp:
                self._display_desc(new_desc)
                if self.myepp is None:
                    print("Energy Performance Preference (EPP):")
                    print("HWP EPP adjustment configures the intel p_state preference policy.")
                    print("\nEPP Ranges:")
                    print("  0x00-0x3F    :    Performance")
                    print("  0x40-0x7F    :    Balanced Performance")
                    print("  0x80-0xBF    :    Balanced Power Savings")
                    print("  0xC0-0xFF    :    Power")
                    print("Settings found in modern Apple computers:")
                    print("  0x00         :    Modern iMac")
                    print("  0x20         :    Modern Mac Mini")
                    print("  0x80         :    Modern MacBook Air")
                    print("  0x90         :    Modern MacBook Pro")
                    print("")
                    curr_desc["start_epp"] = epp
                while True:
                    if self.myepp is None:
                        # Display the hex, ask for a new value
                        print("Default Setting: {} ({})\n".format(epp,self._get_epp_desc(epp)))
                        new = self.u.grab("Enter the new EPP value in hex:  ").upper()
                        if not len(new): new = epp
                        elif new == "Q": self.u.custom_quit()
                        self.myepp = new
                    else:
                        new = self.myepp
                    new = new.replace("0X","")
                    new = "".join([x for x in new if x in "0123456789ABCDEF"])
                    if len(new) != 2:
                        continue
                    # Save the changes
                    ind = str_data.find(self.epp_find)
                    str_data = str_data[:ind+len(self.epp_find)]+new+str_data[ind+len(self.epp_find)+2:]
                    curr_desc["end_epp"] = new
                    break
            if perfbias:
                self._display_desc(new_desc)
                if self.myperfbias is None:
                    print("Perf Bias:")
                    print ("Perf-Bias is a performance and energy bias hint used to specify power preference.  Expressed as a range, 0 represents preference for performance, 15 represents preference for maximum power saving.")
                    print("\nPerf Bias Range:")
                    print("  0x00-0x15")
                    print("Settings found in modern Apple computers:")
                    print("  0x01              :    Modern iMac")
                    print("  0x05              :    Modern MacBook Pro & Mac Mini")
                    print("  0x07              :    Modern MacBook Air")
                    print("")
                    curr_desc["start_perfbias"] = perfbias
                while True:
                    if self.myperfbias is None:
                        # Display the hex, ask for a new value
                        print("Default Setting: {} \n".format(perfbias))
                        new = self.u.grab("Enter the new PerfBias value in hex:  ").upper()
                        if not len(new): new = perfbias
                        elif new == "Q": self.u.custom_quit()
                        self.myperfbias = new
                    else:
                        new = self.myperfbias
                    new = new.replace("0X","")
                    new = "".join([x for x in new if x in "0123456789ABCDEF"])
                    if len(new) != 2:
                        continue
                    # Save the changes
                    ind = str_data.find(self.perfbias_find)
                    str_data = str_data[:ind+len(self.perfbias_find)]+new+str_data[ind+len(self.perfbias_find)+2:]
                    curr_desc["end_epp"] = new
                    break
            new_desc.append(curr_desc)
            # Got the new data - convert it and store it
            new_freq.append(plist.wrap_data(binascii.unhexlify(str_data) if sys.version_info > (3,0) else binascii.unhexlify(str_data)))
        print("Additional Energy Savings Options:")
        print("The MacBook Air SMBIOS includes additional properties for power savings, these properties include the following:")
        print("\n")
        print("  * Power Reduced Video Playback")
        print("  * Thermally Optimized Xcode")
        print("  * Power Optimized Screensavers")
        print("  * Power Optimized Slideshows")
        print("  * Power Optimized PhotoBooth")
        print("  * Power Optimized Visualizers")
        print("")
        while True:
            new = self.u.grab("Enable these features (y/N):  ").upper()
            if new == "Y":
                self.plist_data["IOPlatformPowerProfile"]["power_reduced_playback"] = True
                self.plist_data["IOPlatformPowerProfile"]["thermally_optimized_xcode"] = True
                self.plist_data["IOPlatformPowerProfile"]["optimized_screensavers"] = True
                self.plist_data["IOPlatformPowerProfile"]["optimized_slideshows"] = True
                self.plist_data["IOPlatformPowerProfile"]["optimized_photobooth"] = True
                self.plist_data["IOPlatformPowerProfile"]["optimized_visualizers"] = True
            elif new == "N":
                print("Skipping.")
            else:
                continue
            break
        # Save the changes
        self._display_desc(new_desc)
        print("Saving to {}...".format(self.board+".plist"))
        self.plist_data["IOPlatformPowerProfile"]["FrequencyVectors"] = new_freq
        if os.path.exists(self.out):
            print("Found prior Results - removing...")
            shutil.rmtree(self.out,ignore_errors=True)
        os.makedirs(self.out)
        target_plist = os.path.join(self.out,self.board+".plist")
        with open(target_plist,"wb") as f:
            plist.dump(self.plist_data,f)
        # Run the script if found
        if self.rc_path and os.path.exists(self.rc_path):
            print("Running {}...".format(os.path.basename(self.rc_path)))
            cwd = os.getcwd()
            os.chdir(self.out)
            out = self.r.run({"args":["bash",self.rc_path,"-a",target_plist]})
            if out[2] != 0:
                print(out[1])
            out = self.r.run({"args":["bash",self.rc_path,"-k",target_plist]})
            if out[2] != 0:
                print(out[1])
            if self.iasl:
                print("Compiling SSDTs...")
                for x in os.listdir(self.out):
                    if x.startswith(".") or not x.lower().endswith(".dsl"):
                        continue
                    print(" - {}".format(x))
                    out = self.r.run({"args":[self.iasl,x]})
                    if out[2] != 0:
                        print(out[1])
            os.chdir(cwd)
            self.r.run({"args":["open",self.out]})
        print("")
        print("Done.")
        exit()

c = CPUFF()
c.main()
