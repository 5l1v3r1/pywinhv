# Axel '0vercl0k' Souchet - February 7th 2019
import pywinhv as hv
from ctypes import memmove
import sys

def main(argc, argv):
    HypervisorPresent = hv.IsHypervisorPresent()
    print 'HypervisorPresent:', HypervisorPresent
    if not HypervisorPresent:
        return 1

    print '32-bit kernel'.center(80, '=')
    IDT_GPA = 0xffff0000
    CODE_GPA = 0x0

    PartitionOptions = {
        'ProcessorCount' : 1,
        'Name' : '32b kernel'
    }

    with hv.WHvPartition(**PartitionOptions) as Partition:
        print 'Partition created:', Partition

        Vp = Partition.GetVp(0)
        InitialRip = Vp.GetRip()
        assert InitialRip == 0xfff0, 'The initial @rip(%x) does not match with expected value.' % InitialRip
        print 'Initial @rip in VP0:', hex(InitialRip)

        GuestCodePageAddress, _ = Partition.MapCode(
            # inc eax ; ... ; int3
            '\x40' * 0x1337 + '\xcc',
            CODE_GPA
        )

        print 'Mapped GPA:%x backed by memory at %016x' % (
            CODE_GPA,
            GuestCodePageAddress
        )

        Cr0, Gdtr, Idtr = Vp.GetRegisters(
            hv.Cr0,
            hv.Gdtr,
            hv.Idtr
        )

        print 'CR0:', hv.CR0(Cr0)
        print 'GDTR.Base:', hex(Gdtr.Table.Base)
        print 'GDTR.Limit:', hex(Gdtr.Table.Limit)
        print 'IDTR.Base:', hex(Idtr.Table.Base)
        print 'IDTR.Limit:', hex(Idtr.Table.Limit)
        Idtr.Table.Base = IDT_GPA

        Vp.SetRegisters({
            hv.Rip : CODE_GPA,
            hv.Cs : hv.Generate32bCodeSegment(),
            hv.Idtr : Idtr,
            #hv.Cr0 : Cr0.Reg64 | 1
        })
        print 'Partition configured to run 32b kernel code'

        Rip = Vp.GetRip()
        print '@rip in VP0:', hex(Rip)
        assert Rip == CODE_GPA, '@rip(%x) does not match what we assigned to it.' % Rip

        ExitContext, ExitReason = Vp.Run()
        Vp.DumpRegisters()
        print 'Partition exited with:', ExitReason
        hv.DumpExitContext(ExitContext)

        Rip, Rax = Vp.GetRegisters64(
            hv.Rip,
            hv.Rax
        )

        assert Rip == (CODE_GPA + 0x1337), '@rax(%x) does not match the magic value.' % Rax
        assert ExitReason.value == hv.WHvRunVpExitReasonException, 'An exception VMEXIT is expected when the int3 is triggered.'
        assert ExitContext.VpException.ExceptionType == hv.WHvX64ExceptionTypeBreakpointTrap, 'A breakpoint exception is expected.'
    print 'All good!'
    return 0

if __name__ == '__main__':
    sys.exit(main(len(sys.argv), sys.argv))



