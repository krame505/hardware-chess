#define _XOPEN_SOURCE 500

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <termios.h>

static bool initialized = false;
static int ptm;
static void init(void) {
  if (!initialized) {
    ptm = open("/dev/ptmx", O_RDWR);

    // Set nonblocking read
    int flags = fcntl(ptm, F_GETFL, 0);
    fcntl(ptm, F_SETFL, flags | O_NONBLOCK);

    // Set raw mode
    struct termios ptm_attr;
    tcgetattr(ptm,&ptm_attr);
    ptm_attr.c_lflag &= (~(ICANON|ECHO));
    ptm_attr.c_cc[VTIME] = 0;
    ptm_attr.c_cc[VMIN] = 1;
    tcsetattr(ptm,TCSANOW,&ptm_attr);
    
    grantpt(ptm);
    unlockpt(ptm);
    printf("Initialized simulated serial device at %s\n", ptsname(ptm));

    initialized = true;
  }
}

static void cleanup(void) {
  if (initialized) {
    close(ptm);
    initialized = false;
  }
}

unsigned rxData(void) {
  init();
  char c;
  if (read(ptm, &c, 1) > 0) {
    return c & (unsigned)0xff;
  } else if (errno == EAGAIN) {
    // No data to read, do nothing
  } else if (errno == EIO) {
    // Connection was closed
    printf("Simulated connection closed, exiting\n");
    cleanup();
    exit(0);
  } else {
    perror("PTY read error");
  }
  return -1;
}

void txData(unsigned byte) {
  init();
  char c = byte;
  if (write(ptm, &c, 1) != 1) {
    perror("PTY write error");
  }
}
