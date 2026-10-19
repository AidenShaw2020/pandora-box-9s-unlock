#include <stdio.h>
#include <errno.h>
#include <string.h>
int main(int argc,char **argv){
 const char *attrs[]={"cid","csd","serial","scr",NULL};
 const char *base=argc>1?argv[1]:"/sys/class/mmc_host/mmc0/mmc0:0001";
 for(int i=0;attrs[i];i++){
  char path[512];unsigned char data[80];snprintf(path,sizeof path,"%s/%s",base,attrs[i]);
  FILE *f=fopen(path,"rb");if(!f){printf("%s ERROR %s\n",attrs[i],strerror(errno));continue;}
  size_t n=fread(data,1,sizeof data,f);printf("%s bytes=%u hex=",attrs[i],(unsigned)n);
  for(size_t j=0;j<n;j++){printf("%02x",data[j]);}
  printf("\n");fclose(f);
 }
 return 0;
}
