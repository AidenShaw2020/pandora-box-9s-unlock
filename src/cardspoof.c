/* Pandora 9S: reproduce the application-visible identity from the vendor kernel.
 * Values deliberately differ from the physical card registers read over SPI.
 * Verified with the unchanged vendor ck() against the original disk image. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/syscall.h>
#include <errno.h>
#include "card_identity.h"
#define VERSION "pandora-9s-profile-v1"
static const char *profile(void) {
 return "kernel";
}
static void note(const char *path,const char *val) {
 int saved=errno; const char *log=getenv("PANDORA_CARD_LOG");
 if(!log)log="/mnt/udisk/log/cardspoof_kernel.txt";
 if(log && *log) {
  char b[512]; int n=snprintf(b,sizeof b,"%s pid=%ld profile=%s %s -> %s\n",VERSION,(long)getpid(),profile(),path,val);
  if(n>0 && n<(int)sizeof b) {
   int fd=syscall(SYS_open,log,O_WRONLY|O_CREAT|O_APPEND,0644);
   if(fd>=0){syscall(SYS_write,fd,b,(size_t)n);syscall(SYS_close,fd);}
  }
 }
 errno=saved;
}
__attribute__((constructor)) static void loaded(void){note("loaded",VERSION);}
static const char *pick(const char *p,const char *m){
 if(!p||!m||m[0]!='r'||strchr(m,'+')||strncmp(p,"/sys/",5)||!strstr(p,"mmc"))return NULL;
 const char *leaf=strrchr(p,'/'); if(!leaf)return NULL;
 if(!strcmp(leaf,"/cid"))return PANDORA_CID;
 if(!strcmp(leaf,"/csd"))return PANDORA_CSD;
 if(!strcmp(leaf,"/serial"))return PANDORA_SERIAL;
 if(!strcmp(leaf,"/scr"))return PANDORA_SCR;
 return NULL;
}
FILE *fopen(const char *p,const char *m){
 static FILE *(*real)(const char*,const char*);
 if(!real)real=dlsym(RTLD_NEXT,"fopen");
 const char *s=pick(p,m);if(s){note(p,s);return fmemopen((void*)s,strlen(s),"r");}
 return real(p,m);
}
FILE *fopen64(const char *p,const char *m){
 static FILE *(*real)(const char*,const char*);
 if(!real)real=dlsym(RTLD_NEXT,"fopen64");
 const char *s=pick(p,m);if(s){note(p,s);return fmemopen((void*)s,strlen(s),"r");}
 return real(p,m);
}
