#!/usr/bin/env python3
import sys, subprocess, time


class Disk:
    ''' Class that allows stats tests to be run on disk objects
    '''
    def __init__(self) -> None:
        ''' Method to initialize disk attributes
        '''
        self.disk = 'sda'
        self.status = 0
        self.proc_stat_begin = None
        self.proc_stat_end = None
        self.sys_stat_begin = None
        self.sys_stat_end = None

    def check_return_code(self, ret_val: int, error_msg: str, *output: list) -> None:
        ''' Method to check return code 

        @param ret_val: return code of executed command; 0 = pass, 1 = fail
        @param error_msg: error message to print if ret_val = 1
        @param *output: list of passed in arguments to be printed to console
        '''
        if ret_val != 0:
            print(f"ERROR: retval {ret_val}: {error_msg}", file=sys.stderr)
            if self.status == 0:
                self.status = ret_val
            if len(output) > 0:
                for item in output:
                    print(f"output: {item}")

    def disk_setup(self) -> None:
        ''' Method to determine if disk is changing from default to passed in parameter
        '''
        if len(sys.argv) > 1:
            self.disk = sys.argv[1]

    def get_stats(self) -> None:
        ''' Method to generate stats for comparison
        '''
        # Verify there are stats in /sys/block/$DISK/stat
        ret_val = subprocess.run(["test", "-s", f"/sys/block/{self.disk}/stat"], capture_output=True, universal_newlines=True)
        self.check_return_code(ret_val.returncode, f"stat is either empty or nonexistent in /sys/block/{self.disk}/")

        # Get some baseline stats for use later
        self.proc_stat_begin = subprocess.check_output(["grep", "-w", "-m", "1", self.disk, "/proc/diskstats"])
        self.sys_stat_begin = subprocess.check_output(["cat", f"/sys/block/{self.disk}/stat"])

        # Generate some disk activity using hdparm -t
        subprocess.run(["hdparm", "-t", f"/dev/{self.disk}"], stderr=subprocess.DEVNULL)

        # Sleep 5 to let the stats files catch up
        time.sleep(5)

        # Make sure the stats have changed
        self.proc_stat_end = subprocess.check_output(["grep", "-w", "-m", "1", self.disk, "/proc/diskstats"])
        self.sys_stat_end = subprocess.check_output(["cat", f"/sys/block/{self.disk}/stat"])

    def is_nvdimm(self) -> None:
        ''' Method to determine if disk is an NVDIMM. If true, skip all tests.
        '''
        if 'pmem' in self.disk:
            print(f"Disk {self.disk} appears to be an NVDIMM, skipping")
            sys.exit(self.status)

    def run_disk_commands(self, command: list[str], error_msg: str) -> None:
        ''' Helper method to run disk commands

        @param command: list of strs denoting what command to run in shell
        @param error_msg: str denoting the error message to be shown 
        '''
        result = subprocess.run(command, capture_output=True, universal_newlines=True)
        if result.returncode != 0:
            self.check_return_code(result.returncode, error_msg)

    def run_test(self) -> None:
        ''' Main method to run script
        '''
        self.disk_setup()
        self.is_nvdimm()

        self.check_disk(["grep", "-w", "-q", self.disk, "/proc/partitions"], f"Disk {self.disk} not found in /proc/partitions")
        self.check_disk(["grep", "-w", "-q", "-m", "1", self.disk, "/proc/diskstats"], f"Disk {self.disk} not found in /proc/diskstats")
        self.check_disk(["ls", f"/sys/block/*{self.disk}*", ">/dev/null", "2>&1"], f"Disk {self.disk} not found in /sys/block")

        self.get_stats()

        if self.proc_stat_begin == self.proc_stat_end:
            self.check_return_code(1, "Stats in /proc/diskstats did not change", self.proc_stat_begin, self.proc_stat_end)

        if self.sys_stat_begin == self.sys_stat_end:
            self.check_return_code(1, f"Stats in /sys/block/{self.disk}/stat did not change", self.sys_stat_begin, self.sys_stat_end)

        if self.status == 0:
            print(f"PASS: Finished testing stats for {self.disk}")

        sys.exit(self.status)


if __name__ == "__main__":
   disk = Disk()
   disk.run_test()