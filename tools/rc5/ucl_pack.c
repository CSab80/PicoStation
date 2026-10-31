/* Host-only utility. UCL is GPL-2.0-or-later; see third_party/ucl/COPYING. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ucl/ucl.h>
int main(int argc,char **argv) {
    if(argc!=3)return 2;
    FILE *f=fopen(argv[1],"rb");if(!f)return 3;
    fseek(f,0,SEEK_END);long length=ftell(f);rewind(f);
    if(length<1||length>2000000)return 4;
    unsigned char *in=malloc(length),*out=malloc(length*2+65536),*check=malloc(length);
    if(!in||!out||!check||fread(in,1,length,f)!=(size_t)length)return 5;
    fclose(f);if(ucl_init()!=UCL_E_OK)return 6;
    struct ucl_compress_config_t conf;memset(&conf,0xff,sizeof(conf));conf.bb_size=8;conf.bb_endian=0;
    ucl_uint n=length*2+65536,unpacked=length;
    if(ucl_nrv2e_99_compress(in,length,out,&n,0,10,&conf,0)!=UCL_E_OK)return 7;
    if(ucl_nrv2e_decompress_safe_8(out,n,check,&unpacked,0)!=UCL_E_OK||unpacked!=(ucl_uint)length||memcmp(in,check,length))return 8;
    f=fopen(argv[2],"wb");if(!f)return 9;
    if(fwrite(out,1,n,f)!=n||fclose(f))return 10;
    fprintf(stderr,"NRV2E verified: %ld -> %u bytes\n",length,(unsigned)n);
    free(in);free(out);free(check);return 0;
}
