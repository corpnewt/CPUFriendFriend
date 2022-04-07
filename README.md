# CPUFriendFriend

This Py script will inspect the frequency vectors of the X86PlatformPlugin plist matching your SMBIOS configuration and leverage Acidanthera's CPUFriend ResourceConverter to help you optimize your power management configuration.

This script only generates the CPUFriendDataProvider.kext and ssdt_data.dsl/.aml files - those still **require** Acidanthera's [CPUFriend](https://github.com/acidanthera/CPUFriend) kext to function.

See [CPUFriend's Instructions](https://github.com/acidanthera/CPUFriend/blob/master/Instructions.md) for when it should (or shouldn't) be used, installation instructions, and other info.

## Low Frequency Mode (LFM)

LFM is the lowest frequency at which your CPU should operate when completely idle.  This is the first configuration item prompted by CPUFriendFriend.  It allows you the opportunity to optimize beyond what Apple configures as a default for each model, as it may not be the correct match for your CPU.  To determine the LFM, look your CPU up on Intel's Ark website and convert the TDP-down frequency to Hex.

### Example
To convert the default frequency of 1300MHz to Hex, convert only the number in GHz.

```
$ echo "obase=16; 13" | bc
D
```

Enter 0D to set the LFM attribute to 1300MHz.  For the most common TDP-down value of 800MHz use 08.

To find the appropriate frequency for your system, refer to Intel's CPU documentation for your processor.  The LFM frequency may also be documented as TDP-Down.

## Energy Performance Preference (EPP)

The EPP value dictates how quickly the CPU will scale from the lowest TDP to full clock rate or turbo.  The EPP accepts a range from 00 to C0, however the table below provides general guidance and are the values used by other operating systems.

|Hex Value|Relative Profile|
|---|---|
|0x00|Performance|
|0x40|Balance performance|
|0x80|Balance power|
|0xC0|Max Power saving|

A value of 00 will minimize the time to scale the CPU, providing the best performance while C0 will preference battery life and scale more slowly.

## Perf Bias

Perf Bias is a register on many modern Intel Processors which sets a policy preference for performance vs energy savings.  Perf Bias is a configurable dial ranging from 0 (Performance) to 15 (Energy Savings).  The processor utilizes perf bias to help influence how the processor utilizes C and P states.

## Execution

```
$ git clone https://github.com/corpnewt/CPUFriendFriend.git
$ cd CPUFriendFriend
$ ./CPUFriendFriend.command
```

Once completed, you will be presented with both SSDT and Kext versions of CPUFriendDataProvider data.  Choose the method that you prefer, and add it along with CPUFriend.kext to CLOVER.

## Credits

- PMHeart and Acidanthera for creating and maintaining [CPUFriend](https://github.com/acidanthera/CPUFriend)
