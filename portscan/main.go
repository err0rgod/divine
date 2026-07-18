package main

import (
	"flag"
	"fmt"
	"net"
	"sort"
	"sync"
	"time"
)

func main() {
	host := flag.String("host", "127.0.0.1", "target host to scan")
	start := flag.Int("start", 100, "start port (inclusive)")
	end := flag.Int("end", 65000, "end port (inclusive)")
	workers := flag.Int("workers", 500, "number of concurrent workers")
	timeout := flag.Duration("timeout", 500*time.Millisecond, "dial timeout per port")
	flag.Parse()

	if *start < 1 || *end > 65535 || *start > *end {
		fmt.Println("invalid port range")
		return
	}

	fmt.Printf("Scanning %s ports %d-%d (%d workers, %s timeout)\n",
		*host, *start, *end, *workers, *timeout)

	ports := make(chan int, *workers)
	results := make(chan int)

	var wg sync.WaitGroup
	for i := 0; i < *workers; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for p := range ports {
				addr := net.JoinHostPort(*host, fmt.Sprintf("%d", p))
				conn, err := net.DialTimeout("tcp", addr, *timeout)
				if err == nil {
					conn.Close()
					results <- p
				}
			}
		}()
	}

	// Collect open ports.
	var open []int
	var collect sync.WaitGroup
	collect.Add(1)
	go func() {
		defer collect.Done()
		for p := range results {
			open = append(open, p)
		}
	}()

	begin := time.Now()
	for p := *start; p <= *end; p++ {
		ports <- p
	}
	close(ports)

	wg.Wait()
	close(results)
	collect.Wait()

	sort.Ints(open)
	fmt.Printf("\nDone in %s. %d open port(s):\n", time.Since(begin).Round(time.Millisecond), len(open))
	for _, p := range open {
		fmt.Printf("  %d/tcp open\n", p)
	}
}
