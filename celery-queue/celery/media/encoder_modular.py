import os
import subprocess
import logging
import boto3
import errno

class Encoder():
    "call start_encoder method with argument input_file and output_folder to start encoding. Note:sanitize input and no spaces in the name of files"
    output_folder = ""
    input_file = ""
    width, height = 0, 0
    quality_of_file = 0
    codec = "h264"
    lensec=0

    #ffmpeg code
    # format(input_file,output_file) -kepp output format in aac
    audio_extract = "ffmpeg -i {0} -b:a 54k -ac 1 -vn -acodec copy {1}"
    #format(input_aac_from_audio_extract,output_file)
    audio_tomp4 = "ffmpeg -i {0} -b:a 50k -acodec aac {1}"
    # format(input_file,output-file)
    video_extract = "ffmpeg -i {0} -c copy -an {1}"
    # format(input_file)
    video_lensec = "ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {}"
    # format(input_file)
    h264check = "ffprobe -loglevel error -select_streams v -show_entries stream=codec_name -of default=nw=1:nk=1 {0}"
    # format(input_file,crf,output_fps,2*output_fps,output_filename)
    h264codeencodecrf = "ffmpeg -i {0} -movflags +faststart -bf 2 -coder 1 -pix_fmt yuv420p -crf {1} -filter:v fps=fps={2} -g {3} {4}"
    # format(input_file,out_fps,2*out_fps,output_file)
    encode480p = "ffmpeg -i {0} -s hd480 -profile:v high -bf 2 -coder 1 -c:v libx264 -movflags +faststart -pix_fmt yuv420p -crf 21 -filter:v fps=fps={1} -g {2} -keyint_min {2} -c:a aac -strict -2 {3}"
    # format(input_file,out_fps,2*out_fps,output_file)
    encode720p = "ffmpeg -i {0} -s hd720 -profile:v high -bf 2 -coder 1 -c:v libx264 -movflags +faststart -pix_fmt yuv420p -crf 21 -filter:v fps=fps={1} -g {2} -keyint_min {2} -c:a aac -strict -2 {3}"
    #format(input_file,out_fps,2*out_fps,output_file)
    encode1080p = "ffmpeg -i {0} -s hd1080 -profile:v high -bf 2 -coder 1 -c:v libx264 -movflags +faststart -pix_fmt yuv420p -crf 21 -filter:v fps=fps={1} -g {2} -keyint_min {2} -c:a aac -strict -2 {3}"
    # format(input_file,out_fps,2*out_fps,output_file)
    encodeother = "ffmpeg -i {0} -profile:v high -bf 2 -coder 1 -c:v libx264 -movflags +faststart -pix_fmt yuv420p -crf 21 -filter:v fps=fps={1} -g {2} -keyint_min {2} -c:a aac -strict -2 {3}"

    def awss3config(self,aws_access_key_id,aws_secret_access_key,aws_region):
        boto_kwargs = {
                 "aws_access_key_id": aws_access_key_id,
                 "aws_secret_access_key": aws_secret_access_key,
                 "region_name": aws_region,
            }
        s3_client = boto3.Session(**boto_kwargs).client("s3")
        return s3_client

    def __init__(self, input_file, output_folder,aws_bucket,aws_access_key_id,aws_secret_key,aws_region):
        self.input_file = input_file
        self.output_folder = output_folder
        logging.basicConfig(
            filename='error.log', level=logging.WARNING)
        self.filenm = os.path.basename(self.input_file)
        self.s3_client=self.awss3config(aws_access_key_id,aws_secret_key,aws_region)
        self.aws_bucket=aws_bucket
        self.ret = []

    def uploadtos3(self,filepath,aws_path):
        self.s3_client.upload_file(filepath,self.aws_bucket,aws_path)


    def resolution(self):
        "returns resolutio of input file and sets codec of input file"
        codeccheck = (self.h264check).format(self.input_file)
        codec_in=0
        try:
           codec_in = subprocess.check_output(codeccheck.split(" "))
        except:
            logging.warning("warning at rresolution ,directory:{}",os.getcwd())
            codec_in = subprocess.check_output(codeccheck.split(" "))   #weird but to retry
        if(codec_in != self.codec):
            self.codec = codec_in
        output = ""
        try:
           output = subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                                             '-show_entries', 'stream=width,height', '-of', 'csv=p=0', self.input_file])
        except:
            output = subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                                              '-show_entries', 'stream=width,height', '-of', 'csv=p=0', self.input_file])  # weird but ok,since it may fail first time
        output = output.strip()
        output = output.decode("utf-8")
        output = output.split(',')
        self.width, self.height = int(output[0]), int(output[1])
        return int(output[0]), int(output[1])

    def quality_check(self):
        "checks quality of input file"
        width, height = self.resolution()
        if(height >= 1440):
            self.quality_of_file = 1440
        elif(height >= 1080):
            self.quality_of_file = 1080
        elif(height >= 720):
            self.quality_of_file = 720
        elif(height >= 576):
            self.quality_of_file = 576
        elif(height >= 480):
            self.quality_of_file = 480
        elif(height >= 360):
            self.quality_of_file = 360
        else:
            self.quality_of_file = 240
        return self.quality_of_file
    
    def getduration(self):
        "get duration of video"
        lensec_code = (self.video_lensec).format(self.input_file)
        output=""
        try:
            output=subprocess.check_output(lensec_code.split(" "))
        except:
            output = subprocess.check_output(lensec_code.split(" "))   #weird but sometimes fails .that is why second try
        output = output.strip()
        output = output.decode("utf-8")
        self.lensec=float(output)
        return float(output)

    def extract_audio(self):
        "extract audio and keep original no sound video in root folder.beware self.input_file after this changes"
        try:
           os.mkdir(self.output_folder+'/'+'audio')
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise
            pass
        filenm = self.filenm
        inp = filenm.rsplit('.', 1)[0]
        ext = filenm.rsplit('.', 1)[1]
        outaudiocode = self.audio_extract.format(
            self.input_file, (self.output_folder+'/'+'audio'+'/'+(inp+'.'+'aac')))
        res = subprocess.call(outaudiocode.split(" "))
        if(res != 0):
            res = subprocess.call(outaudiocode.split(" "))
        if(res != 0):
           logging.warning('audio encoder for aac at width:{} height:{} codec:{} input_file:{}'.format(
               self.width, self.height, self.codec, self.input_file))
        else:
            outaudiomp4 = self.audio_tomp4.format(
                (self.output_folder+'/'+'audio'+'/'+(inp+'.'+'aac')), self.output_folder+'/'+'audio'+'/'+(inp+'.'+'mp4'))
            res = subprocess.call(outaudiomp4.split(" "))
            if(res !=0):
                res = subprocess.call(outaudiomp4.split(" "))
            if(res != 0):
               logging.warning('audio encoder for mp4 at width:{} height:{} codec:{} input_file:{}'.format(
               self.width, self.height, self.codec, self.input_file))
            else:
                os.remove(self.output_folder+'/'+'audio'+'/'+(inp+'.'+'aac'))
                self.uploadtos3(self.output_folder+'/'+'audio'+'/'+(inp+'.'+'mp4'),
                                self.output_folder+'/'+'audio'+'/'+(inp+'.'+'mp4'))
                os.remove(self.output_folder+'/'+'audio'+'/'+(inp+'.'+'mp4'))
        #now no sound video extract
        outvideocode = self.video_extract.format(
            self.input_file, self.output_folder+'/'+'original'+'.'+ext)
        res = subprocess.call(outvideocode.split(" "))
        if(res != 0):
            res = subprocess.call(outvideocode.split(" "))
        if(res != 0):
            logging.warning('original video to audio removal at width:{} height:{} codec:{} self.input_file:{}'.format(
                self.width, self.height, self.codec, self.input_file))
        else:
            try:
               os.rename(self.output_folder+'/'+'original'+'.' +
                         ext, self.output_folder+'/'+self.filenm)
            except:
                os.remove(self.output_folder+'/'+self.filenm)
                os.rename(self.output_folder+'/'+'original'+'.' +
                          ext, self.output_folder+'/'+self.filenm)
            
    def encode1080p1by12(self):
            path = "1080p1by12"
            try:
              os.mkdir(path)
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
                pass
            out1080code = (self.encode1080p).format(self.filenm, 1/12,2/12,path+'/'+self.filenm)
            res = subprocess.call(out1080code.split(" "))
            if(res != 0):
                res = subprocess.call(out1080code.split(" "))
            if(res != 0):
                logging.warning('Video encoder at 1080p1/12 width:{} height:{} codec:{} input_file:{}'.format(self.width, self.height, self.codec,self.input_file))
                return 1
            else:
                self.ret.append(path)
                self.uploadtos3(path+'/'+self.filenm,
                                self.output_folder+'/'+path+'/'+self.filenm)
                os.remove(path+'/'+self.filenm)
                return 0

    def encode1080p1by18(self):
            path = "1080p1by18"
            try:
              os.mkdir(path)
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
                pass
            out1080code = (self.encode1080p).format(self.filenm, 1/18,2/18,path+'/'+self.filenm)
            res = subprocess.call(out1080code.split(" "))
            if(res != 0):
                res = subprocess.call(out1080code.split(" "))
            if(res != 0):
                logging.warning('Video encoder at 1080p1/18 width:{} height:{} codec:{} input_file:{}'.format(self.width, self.height, self.codec,self.input_file))
                return 1
            else:
                self.ret.append(path)
                self.uploadtos3(path+'/'+self.filenm,
                                self.output_folder+'/'+path+'/'+self.filenm)
                os.remove(path+'/'+self.filenm)
                return 0

    def encode1080p1by24(self):
            path = "1080p1by24"
            try:
              os.mkdir(path)
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
                pass
            out1080code = (self.encode1080p).format(self.filenm, 1/24, 2/24, path+'/'+self.filenm)
            res = subprocess.call(out1080code.split(" "))
            if(res != 0):
                res = subprocess.call(out1080code.split(" "))
            if(res != 0):
                logging.warning('Video encoder at 1080p1/24 width:{} height:{} codec:{} input_file:{}'.format(
                    self.width, self.height, self.codec, self.input_file))
                return 1
            else:
                self.ret.append(path)
                self.uploadtos3(path+'/'+self.filenm,
                                self.output_folder+'/'+path+'/'+self.filenm)
                os.remove(path+'/'+self.filenm)
                return 0

    def encode480p1by12(self):
            path = "480p1by12"
            try:
              os.mkdir(path)
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
                pass
            out480code=(self.encode480p).format(self.filenm,1/12,2/12,path+'/'+self.filenm)
            res=subprocess.call(out480code.split(" "))
            if(res !=0):
                res = subprocess.call(out480code.split(" "))
            if(res !=0):
                logging.warning('Video encoder at 480p1/12 width:{} height:{} codec:{} input_file:{}'.format(self.width,self.height,self.codec,self.input_file))
                return 1
            else:
                self.ret.append(path)
                self.uploadtos3(path+'/'+self.filenm,
                                self.output_folder+'/'+path+'/'+self.filenm)
                os.remove(path+'/'+self.filenm)
                return 0
    
    def encode480p1by18(self):
            path = "480p1by18"
            try:
              os.mkdir(path)
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
                pass
            out480code=(self.encode480p).format(self.filenm,1/18,2/18,path+'/'+self.filenm)
            res=subprocess.call(out480code.split(" "))
            if(res !=0):
                res = subprocess.call(out480code.split(" "))
            if(res !=0):
                logging.warning('Video encoder at 480p1/18 width:{} height:{} codec:{} input_file:{}'.format(self.width,self.height,self.codec,self.input_file))
                return 1
            else:
                self.ret.append(path)
                self.uploadtos3(path+'/'+self.filenm,
                                self.output_folder+'/'+path+'/'+self.filenm)
                os.remove(path+'/'+self.filenm)
                return 0
    
    def encode480p1by24(self):            
            path = "480p1by24"
            try:
               os.mkdir(path)
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
                pass
            out480code = (self.encode480p).format(
                self.filenm, 1/24, 2/24, path+'/'+self.filenm)
            res = subprocess.call(out480code.split(" "))
            if(res != 0):
                res = subprocess.call(out480code.split(" "))
            if(res != 0):
                logging.warning(
                    'Video encoder at 480p1/24 width:{} height:{} codec:{} input_file:{}'.format(self.width, self.height, self.codec, self.input_file))
                return 1
            else:
                self.ret.append(path)
                self.uploadtos3(path+'/'+self.filenm,
                                self.output_folder+'/'+path+'/'+self.filenm)
                os.remove(path+'/'+self.filenm)
                return 0

    def encode720p1by12(self):
            path = "720p1by12"
            try:
               os.mkdir(path)
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
                pass
            out720code = (self.encode720p).format(
                self.filenm, 1/12, 2/12, path+'/'+self.filenm)
            res = subprocess.call(out720code.split(" "))
            if(res !=0):
                res = subprocess.call(out720code.split(" "))
            if(res !=0):
                logging.warning(
                    'Video encoder at 720p1/12 width:{} height:{} codec:{} input_file:{}'.format(self.width, self.height, self.codec,self.input_file))
                return 1
            else:
                self.ret.append(path)
                self.uploadtos3(path+'/'+self.filenm,
                                self.output_folder+'/'+path+'/'+self.filenm)
                os.remove(path+'/'+self.filenm)
                return 0
            
    def encode720p1by18(self):
            path = "720p1by18"
            try:
               os.mkdir(path)
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
                pass
            out720code = (self.encode720p).format(
                self.filenm, 1/18, 2/18, path+'/'+self.filenm)
            res = subprocess.call(out720code.split(" "))
            if(res !=0):
                res = subprocess.call(out720code.split(" "))
            if(res !=0):
                logging.warning(
                    'Video encoder at 720p1/18 width:{} height:{} codec:{} input_file:{}'.format(self.width, self.height, self.codec,self.input_file))
                return 1
            else:
                self.ret.append(path)
                self.uploadtos3(path+'/'+self.filenm,
                                self.output_folder+'/'+path+'/'+self.filenm)
                os.remove(path+'/'+self.filenm)
                return 0
    
    def encode720p1by24(self):
            path = "720p1by24"
            try:
              os.mkdir(path)
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
                pass
            out720code = (self.encode720p).format(
                self.filenm, 1/24, 2/24, path+'/'+self.filenm)
            res = subprocess.call(out720code.split(" "))
            if(res !=0):
                res = subprocess.call(out720code.split(" "))
            if(res !=0):
                logging.warning(
                    'Video encoder at 720p1/24 width:{} height:{} codec:{} input_file:{}'.format(self.width, self.height, self.codec,self.input_file))
                return 1
            else:
                self.ret.append(path)
                self.uploadtos3(path+'/'+self.filenm,
                                self.output_folder+'/'+path+'/'+self.filenm)
                os.remove(path+'/'+self.filenm)
                return 0

    def encode360p1by12(self):
            path = "360p1by12"
            try:
               os.mkdir(path)
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
                pass
            out360code = (self.encodeother).format(
                self.filenm, 1/12, 2/12, path+'/'+self.filenm)
            res = subprocess.call(out360code.split(" "))
            if(res !=0):
                res = subprocess.call(out360code.split(" "))
            if(res !=0):
                logging.warning(
                    'Video encoder at 360p1/12 width:{} height:{} codec:{} input_file:{}'.format(self.width, self.height, self.codec,self.input_file))
                return 1
            else:
                self.ret.append(path)
                self.uploadtos3(path+'/'+self.filenm,
                                self.output_folder+'/'+path+'/'+self.filenm)
                os.remove(path+'/'+self.filenm)
                return 0

    def encode360p1by18(self):
            path = "360p1by18"
            try:
               os.mkdir(path)
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
                pass
            out360code = (self.encodeother).format(
                self.filenm, 1/18, 2/18, path+'/'+self.filenm)
            res = subprocess.call(out360code.split(" "))
            if(res !=0):
                res = subprocess.call(out360code.split(" "))
            if(res !=0):
                logging.warning(
                    'Video encoder at 360p1/18 width:{} height:{} codec:{} input_file:{}'.format(self.width, self.height, self.codec,self.input_file))
                return 1
            else:
                self.ret.append(path)
                self.uploadtos3(path+'/'+self.filenm,
                                self.output_folder+'/'+path+'/'+self.filenm)
                os.remove(path+'/'+self.filenm)
                return 0

    def encode360p1by24(self):
            path = "360p1by24"
            try:
              os.mkdir(path)
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
                pass
            out360code = (self.encodeother).format(
                self.filenm, 1/24, 2/24, path+'/'+self.filenm)
            res = subprocess.call(out360code.split(" "))
            if(res !=0):
                res = subprocess.call(out360code.split(" "))
            if(res !=0):
                logging.warning(
                    'Video encoder at 360p1/24 width:{} height:{} codec:{} input_file:{}'.format(self.width, self.height, self.codec,self.input_file))
                return 1
            else:
                self.ret.append(path)
                self.uploadtos3(path+'/'+self.filenm,
                                self.output_folder+'/'+path+'/'+self.filenm)
                os.remove(path+'/'+self.filenm)
                return 0

    def encode240p1by12(self):
            path = "240p1by12"
            try:
              os.mkdir(path)
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
                pass
            out240code = (self.encodeother).format(
                self.filenm, 1/12, 2/12, path+'/'+self.filenm)
            res = subprocess.call(out240code.split(" "))
            if(res !=0):
                res = subprocess.call(out240code.split(" "))
            if(res !=0):
                logging.warning(
                    'Video encoder at 240p1/12 width:{} height:{} codec:{} input_file:{}'.format(self.width, self.height, self.codec,self.input_file))
                return 1
            else:
                self.ret.append(path)
                self.uploadtos3(path+'/'+self.filenm,
                                self.output_folder+'/'+path+'/'+self.filenm)
                os.remove(path+'/'+self.filenm)
                return 0

    def encode240p1by18(self):
            path = "240p1by18"
            try:
              os.mkdir(path)
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
                pass
            out240code = (self.encodeother).format(
                self.filenm, 1/18, 2/18, path+'/'+self.filenm)
            res = subprocess.call(out240code.split(" "))
            if(res !=0):
                res = subprocess.call(out240code.split(" "))
            if(res !=0):
                logging.warning(
                    'Video encoder at 240p1/18 width:{} height:{} codec:{} input_file:{}'.format(self.width, self.height, self.codec,self.input_file))
                return 1
            else:
                self.ret.append(path)
                self.uploadtos3(path+'/'+self.filenm,
                                self.output_folder+'/'+path+'/'+self.filenm)
                os.remove(path+'/'+self.filenm)
                return 0

    def encode240p1by24(self):
            path = "240p1by24"
            try:
              os.mkdir(path)
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
                pass
            out240code = (self.encodeother).format(
                self.filenm, 1/24, 2/24, path+'/'+self.filenm)
            res = subprocess.call(out240code.split(" "))
            if(res !=0):
                res = subprocess.call(out240code.split(" "))
            if(res !=0):
                logging.warning(
                    'Video encoder at 240p1/24 width:{} height:{} codec:{} input_file:{}'.format(self.width, self.height, self.codec,self.input_file))
                return 1
            else:
                self.ret.append(path)
                self.uploadtos3(path+'/'+self.filenm,
                                self.output_folder+'/'+path+'/'+self.filenm)
                os.remove(path+'/'+self.filenm)
                return 0
    
    def encodeother1by12(self):
            path = "other1by12"
            try:
              os.mkdir(path)
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
                pass
            out240code = (self.encodeother).format(
                self.filenm, 1/12, 2/12, path+'/'+self.filenm)
            res = subprocess.call(out240code.split(" "))
            if(res != 0):
                res = subprocess.call(out240code.split(" "))
            if(res != 0):
                logging.warning(
                    'Video encoder at other1/5 width:{} height:{} codec:{} input_file:{}'.format(self.width, self.height, self.codec,self.input_file))
                return 1
            else:
                self.ret.append(path)
                self.uploadtos3(path+'/'+self.filenm,
                                self.output_folder+'/'+path+'/'+self.filenm)
                os.remove(path+'/'+self.filenm)
                return 0

    def encodeother1by18(self):
            path = "other1by18"
            try:
              os.mkdir(path)
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
                pass
            out240code = (self.encodeother).format(
                self.filenm, 1/18, 2/18, path+'/'+self.filenm)
            res = subprocess.call(out240code.split(" "))
            if(res != 0):
                res = subprocess.call(out240code.split(" "))
            if(res != 0):
                logging.warning(
                    'Video encoder at other1/18 width:{} height:{} codec:{} input_file:{}'.format(self.width, self.height, self.codec,self.input_file))
                return 1
            else:
                self.ret.append(path)
                self.uploadtos3(path+'/'+self.filenm,
                                self.output_folder+'/'+path+'/'+self.filenm)
                os.remove(path+'/'+self.filenm)
                return 0

    def encodeother1by24(self):
            path = "other1by24"
            try:
              os.mkdir(path)
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
                pass
            out240code = (self.encodeother).format(
                self.filenm, 1/24, 2/24, path+'/'+self.filenm)
            res = subprocess.call(out240code.split(" "))
            if(res != 0):
                res = subprocess.call(out240code.split(" "))
            if(res != 0):
                logging.warning(
                    'Video encoder at other1/24 width:{} height:{} codec:{} input_file:{}'.format(self.width, self.height, self.codec,self.input_file))
                return 1
            else:
                self.ret.append(path)
                self.uploadtos3(path+'/'+self.filenm,
                                self.output_folder+'/'+path+'/'+self.filenm)
                os.remove(path+'/'+self.filenm)
                return 0
        
    def start_encode(self):
        "start the encode"
        self.resolution()
        self.getduration()
        self.quality_check()
        self.extract_audio()
        os.chdir(self.output_folder)
        if(self.quality_of_file == 1440 or self.quality_of_file == 1080):
            if(self.lensec<=1200):
                self.encode1080p1by12()
                self.encode720p1by12()
                self.encode480p1by12()
            elif(self.lensec<=3600):
                self.encode1080p1by18()
                self.encode720p1by18()
                self.encode480p1by18()
            else:
                self.encode1080p1by24()
                self.encode720p1by24()
                self.encode480p1by24()

        elif(self.quality_of_file == 720):
            if(self.lensec<=1200):
                self.encode720p1by12()
                self.encode480p1by12()
            elif(self.lensec<=3600):
                self.encode720p1by18()
                self.encode480p1by18()
            else:
                self.encode720p1by24()
                self.encode480p1by24()

        elif(self.quality_of_file == 576 or self.quality_of_file == 480):
            if(self.lensec<=1200):
                self.encode480p1by12()
                self.encode360p1by12()
            elif(self.lensec<=3600):
                self.encode480p1by18()
                self.encode360p1by18()
            else:
                self.encode480p1by24()
                self.encode360p1by24()
        
        elif(self.quality_of_file == 360):
            if(self.lensec <= 1200):
                self.encode360p1by12()
            elif(self.lensec<=3600):
                self.encode360p1by18()
            else:
                self.encode360p1by24()

        elif(self.quality_of_file == 240):
            if(self.lensec <= 1200):
               self.encode240p1by12()
            elif(self.lensec<=3600):
                self.encode240p1by18()
            else:
                self.encode240p1by24()
        
        else:
            if(self.lensec <=1200):
               self.encodeother1by12()
            elif(self.lensec<=3600):
                self.encodeother1by18()
            else:
                self.encodeother1by24()
        
        self.uploadtos3(self.filenm,
                        self.output_folder+'/'+self.filenm)
        os.remove(self.filenm)
        return self.ret
    
    def __repr__(self):
        return "encode the videos by start_encode method with input_file and output_folder"
        
