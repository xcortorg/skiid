package main

import (
    "flag"
    "fmt"
    "net/netip"
    "os"
    "os/exec"
    "strings"
)

var (
    ipv6interface = flag.String("interface", "eth0", "IPv6 interface")
    ipv6n         = flag.Int("v6_n", 1, "Number of sequential IPv6 addresses")
    startAddrFlag = flag.String("ipv6", "", "Starting IPv6 address")
)

func main() {
    flag.Parse()

    var startAddr netip.Addr
    if *startAddrFlag != "" {
        var err error
        startAddr, err = netip.ParseAddr(*startAddrFlag)
        if err != nil {
            fmt.Printf("Error parsing IPv6 address from flag: %v\n", err)
            return
        }
    } else {
        startAddrStr := os.Getenv("IPV6")
        if startAddrStr == "" {
            fmt.Println("Error: IPV6 environment variable not set and no IPv6 flag provided")
            return
        }
        var err error
        startAddr, err = netip.ParseAddr(startAddrStr)
        if err != nil {
            fmt.Printf("Error parsing IPv6 address from environment variable: %v\n", err)
            return
        }
    }

    for i := 0; i < *ipv6n; i++ {
        addr := startAddr.Next()
        cmd := exec.Command("sudo", "ip", "-6", "addr", "add", fmt.Sprintf("%s/64", addr.String()), "dev", *ipv6interface)
        output, err := cmd.CombinedOutput()
        if err != nil {
            if strings.Contains(string(output), "RTNETLINK answers: File exists") {
                fmt.Printf("Address %s already exists, skipping...\n", addr.String())
            } else {
                fmt.Printf("Error running command for address %s: %v\nOutput: %s\n", addr.String(), err, output)
                return
            }
        } else {
            fmt.Printf("Added IPv6 address %s to interface %s\n", addr.String(), *ipv6interface)
        }
        startAddr = addr
    }
}
