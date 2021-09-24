import os
import subprocess
import logging
import boto3
import errno

class AdptEncoder():
    "call start_encoder method with argument input_file and output_folder to start encoding. Note:sanitize input and no spaces in the name of files"
    output_folder = ""
    input_file = ""
    width, height = 0, 0
    quality_of_file = 0
    codec = "h264"
    lensec=0
    #format(input_file,output_webm)
    audio_extract="ffmpeg -i {} -vn -acodec libvorbis -ab 55k -dash 1 {}"
    #format(duration_of_video,output_webm_file)
    null_audio="ffmpeg -f lavfi -i anullsrc -t {0} -c:a libvorbis -dash 1 {1}"
    # format(input_file,output-file)
    video_extract = "ffmpeg -i {0} -c copy -an {1}"
    # format(input_file)
    video_lensec = "ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {}"
    # format(input_file)
    h264check = "ffprobe -loglevel error -select_streams v -show_entries stream=codec_name -of default=nw=1:nk=1 {0}"
    #format(input,fps,2*fps,self.filenm)
    encode480p="ffmpeg -i {0} -c:v libvpx-vp9 -keyint_min {2} -movflags +faststart -pix_fmt yuv420p -crf 17 -filter:v fps=fps={1} -tile-columns 4 -frame-parallel 1  -f webm -dash 1 -s hd480 -an -b:v 100k -dash 1 {3}"
    #format(input,fps,2*fps,self.filenm)
    encode720p="ffmpeg -i {0} -c:v libvpx-vp9 -keyint_min {2} -movflags +faststart -pix_fmt yuv420p -crf 17 -filter:v fps=fps={1} -tile-columns 4 -frame-parallel 1  -f webm -dash 1 -s hd720 -an -b:v 160k -dash 1 {3}"
    #format(input,fps,2*fps,self.filenm)
    encode1080p="ffmpeg -i {0} -c:v libvpx-vp9 -keyint_min {2} -movflags +faststart -pix_fmt yuv420p -crf 17 -filter:v fps=fps={1} -tile-columns 4 -frame-parallel 1  -f webm -dash 1 -s hd1080 -an -b:v 230k -dash 1 {3}"
    #format(input,fps,2*fps,self.filenm)
    encode360p = "ffmpeg -i {0} -c:v libvpx-vp9 -keyint_min {2} -movflags +faststart -pix_fmt yuv420p -crf 17 -filter:v fps=fps={1} -tile-columns 4 -frame-parallel 1  -f webm -dash 1 -s 640x360  -an -b:v 80k -dash 1 {3}"
    #format(input,fps,2*fps,self.filenm)
    encodeother="ffmpeg -i {0} -c:v libvpx-vp9 -keyint_min {2} -movflags +faststart -pix_fmt yuv420p -crf 17 -filter:v fps=fps={1} -tile-columns 4 -frame-parallel 1  -f webm -dash 1 -an -b:v 240k -dash 1 {3}"
    #format
    dashmanifest = "ffmpeg \
  -f webm_dash_manifest -i video_160x90_250k.webm \
  -f webm_dash_manifest -i video_320x180_500k.webm \
  -f webm_dash_manifest -i video_640x360_750k.webm \
  -f webm_dash_manifest -i video_1280x720_1500k.webm \
  -f webm_dash_manifest -i my_audio.webm \
  -c copy \
  -map 0 -map 1 -map 2 -map 3 -map 4 \
  -f webm_dash_manifest \
  -adaptation_sets 'id=0,streams=0,1,2,3 id=1,streams=4' \
  my_video_manifest.mpd"

    def awss3config(self, aws_access_key_id, aws_secret_access_key, aws_region):
        boto_kwargs = {
            "aws_access_key_id": aws_access_key_id,
            "aws_secret_access_key": aws_secret_access_key,
            "region_name": aws_region,
        }
        s3_client = boto3.Session(**boto_kwargs).client("s3")
        return s3_client
    
    def __init__(self, input_file, output_folder, aws_bucket, aws_access_key_id, aws_secret_key, aws_region):
        self.input_file = input_file
        self.output_folder = output_folder
        logging.basicConfig(
            filename='error.log', level=logging.WARNING)
        self.filenm = os.path.basename(self.input_file)
        self.s3_client = self.awss3config(
            aws_access_key_id, aws_secret_key, aws_region)
        self.aws_bucket = aws_bucket
        self.ret = []

    def uploadtos3(self, filepath, aws_path):
        self.s3_client.upload_file(filepath, self.aws_bucket, aws_path)
    
    def resolution(self):
        "returns resolutio of input file and sets codec of input file"
        codeccheck = (self.h264check).format(self.input_file)
        codec_in = 0
        try:
           codec_in = subprocess.check_output(codeccheck.split(" "))
        except:
            logging.warning(
                "warning at rresolution ,directory:{}".format(os.getcwd()))
            codec_in = subprocess.check_output(
                codeccheck.split(" "))  # weird but to retry
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
        output = ""
        try:
            output = subprocess.check_output(lensec_code.split(" "))
        except:
            # weird but sometimes fails .that is why second try
            output = subprocess.check_output(lensec_code.split(" "))
        output = output.strip()
        output = output.decode("utf-8")
        self.lensec = float(output)
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
            self.input_file, (self.output_folder+'/'+(inp+'audio'+'.webm')))
        res = subprocess.call(outaudiocode.split())
        if(res != 0):
            res = subprocess.call(outaudiocode.split())
        if(res != 0):
           logging.warning('audio-encoder error:Probably no-audio or cant encode,continuing blank-audio, for vorbis at width:{} height:{} codec:{} input_file:{}'.format(
               self.width, self.height, self.codec, self.input_file))
           #now generate a blank audio of video length
           outaudiocode=self.null_audio.format(self.lensec,(self.output_folder+'/'+(inp+'audio'+'.webm')))
           res= subprocess.call(outaudiocode.split())
           if(res != 0):
             res= subprocess.call(outaudiocode.split())
           if(res != 0):
              logging.warning('audio-encoder for blank-audio error, for vorbis at width:{} height:{} codec:{} input_file:{}'.format(
               self.width, self.height, self.codec, self.input_file))
           else:
               self.uploadtos3(self.output_folder+'/'+(inp+'audio'+'.webm'),
                            self.output_folder+'/'+(inp+'audio'+'.webm'))

        else:
            self.uploadtos3(self.output_folder+'/'+(inp+'audio'+'.webm'),
                            self.output_folder+'/'+(inp+'audio'+'.webm'))
        #now video extract
        
        outvideocode = self.video_extract.format(
            self.input_file, self.output_folder+'/'+'original'+'.'+ext)
        res = subprocess.call(outvideocode.split())
        if(res != 0):
            res = subprocess.call(outvideocode.split())
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

    def encode1080pvideo(self,folder="1080p1by6",fps=1/6):
            subname = folder
            
            out1080code = (self.encode1080p).format(
                self.filenm, fps, 2*fps, self.filenm.rsplit('.', 1)[0]+subname+'.webm')
            res = subprocess.call(out1080code.split())
            if(res != 0):
                res = subprocess.call(out1080code.split())
            if(res != 0):
                logging.warning('Video encoder at 1080p width:{} height:{} codec:{} input_file:{}'.format(
                    self.width, self.height, self.codec, self.input_file))
                return 1
            else:
                self.ret.append(subname)
                self.uploadtos3(self.filenm.rsplit('.', 1)[0]+subname+'.webm',
                                self.output_folder+'/'+self.filenm.rsplit('.', 1)[0]+subname+'.webm')
                return 0
            
    def encode720pvideo(self, folder="720p1by6", fps=1/6):
            subname= folder
            out720code = (self.encode720p).format(
                self.filenm, fps, 2*fps, self.filenm.rsplit('.', 1)[0]+subname+'.webm')
            res = subprocess.call(out720code.split())
            if(res != 0):
                res = subprocess.call(out720code.split())
            if(res != 0):
                logging.warning(
                    'Video encoder at 720p1 width:{} height:{} codec:{} input_file:{}'.format(self.width, self.height, self.codec, self.input_file))
                return 1
            else:
                self.ret.append(subname)
                self.uploadtos3(self.filenm.rsplit('.', 1)[0]+subname+'.webm',
                                self.output_folder+'/'+self.filenm.rsplit('.', 1)[0]+subname+'.webm')
                return 0
            
    def encode480pvideo(self, folder="480p1by6", fps=1/6):
            subname = folder
            
            out480code = (self.encode480p).format(
                self.filenm, fps, 2*fps, self.filenm.rsplit('.', 1)[0]+subname+'.webm')
            print(out480code)
            res = subprocess.call(out480code.split())
            if(res != 0):
                res = subprocess.call(out480code.split())
            if(res != 0):
                logging.warning(
                    'Video encoder at 480p1 width:{} height:{} codec:{} input_file:{}'.format(self.width, self.height, self.codec, self.input_file))
                return 1
            else:
                self.ret.append(subname)
                self.uploadtos3(self.filenm.rsplit('.', 1)[0]+subname+'.webm',
                                self.output_folder+'/'+self.filenm.rsplit('.', 1)[0]+subname+'.webm')
                return 0
            
    def encode360pvideo(self, folder="360p1by6", fps=1/6):
            subname = folder
            
            out360code = (self.encode360p).format(
                self.filenm, fps, 2*fps, self.filenm.rsplit('.', 1)[0]+subname+'.webm')
            print(out360code)
            res = subprocess.call(out360code.split())
            if(res != 0):
                res = subprocess.call(out360code.split())
            if(res != 0):
                logging.warning(
                    'Video encoder at 360p width:{} height:{} codec:{} input_file:{}'.format(self.width, self.height, self.codec, self.input_file))
                return 1
            else:
                self.ret.append(subname)
                self.uploadtos3(self.filenm.rsplit('.', 1)[0]+subname+'.webm',
                                self.output_folder+'/'+self.filenm.rsplit('.', 1)[0]+subname+'.webm')
                return 0

    def encodeothervideo(self, folder="other1by6", fps=1/6):
            subname = folder
            
            out360code = (self.encodeother).format(
                self.filenm, fps, 2*fps, self.filenm.rsplit('.', 1)[0]+subname+'.webm')
            res = subprocess.call(out360code.split())
            if(res != 0):
                res = subprocess.call(out360code.split())
            if(res != 0):
                logging.warning(
                    'Video encoder at 360p width:{} height:{} codec:{} input_file:{}'.format(self.width, self.height, self.codec, self.input_file))
                return 1
            else:
                self.ret.append(subname)
                self.uploadtos3(self.filenm.rsplit('.', 1)[0]+subname+'.webm',
                                self.output_folder+'/'+self.filenm.rsplit('.', 1)[0]+subname+'.webm')
                return 0
    
    def mpdgeneration(self):
        num=[]
        ret=self.ret
        filenm=self.filenm
        for i in range(len(self.ret)):
            num.append(i)
        com = "ffmpeg "
        side = "-f webm_dash_manifest -i {} "
        mid = "-c copy "
        mapping = "-map {} "
        end = "-f webm_dash_manifest -adaptation_sets \"id=0,streams={0} id=1,streams={1}\" {2}"
        for i in ret:
            com = com+side.format(filenm.rsplit('.',1)[0]+i+'.webm')
        com = com+side.format(
                                           filenm.rsplit('.',1)[0]+'audio'+'.webm')
        com = com+mid
        for i in range(len(ret)+1):
            com = com+mapping.format(i)
        com = com+end.format(','.join(str(x) for x in num),
                             len(num), filenm.rsplit('.',1)[0]+'.mpd')
        #juggad is done
        print(com)
        res=subprocess.Popen(com, shell=True,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
        if(res != 0):
                res = subprocess.Popen(com, shell=True,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
        if(res != 0):
                logging.warning(
                    'Video encoder at mpd width:{} height:{} codec:{} input_file:{}'.format(self.width, self.height, self.codec, self.input_file))
                return 1
        else:
            self.uploadtos3(self.filenm.rsplit('.', 1)[0]+'.mpd',
                            self.output_folder+'/'+self.filenm.rsplit('.', 1)[0]+'.mpd')
            os.remove(self.filenm.rsplit('.', 1)[0]+'.mpd')
        return 0
            
    def cleanup(self):
        for i in self.ret:
            os.remove(self.filenm.rsplit('.',1)[0]+i+'.webm')
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
                    self.encode1080pvideo('1080p1by4',1/4)
                    self.encode720pvideo('720p1by4',1/4)
                    self.encode480pvideo('480p1by4',1/4)
                elif(self.lensec<=3600):
                    self.encode1080pvideo('1080p1by6',1/6)
                    self.encode720pvideo('720p1by6',1/6)
                    self.encode480pvideo('480p1by6',1/6)
                else:
                    self.encode1080pvideo('1080p1by10',1/10)
                    self.encode720pvideo('720p1by10',1/10)
                    self.encode480pvideo('480p1by10',1/10)
            elif(self.quality_of_file == 720):
                if(self.lensec<=1200):
                    self.encode720pvideo('720p1by4',1/4)
                    self.encode480pvideo('480p1by4',1/4)
                elif(self.lensec<=3600):
                    self.encode720pvideo('720p1by6',1/6)
                    self.encode480pvideo('480p1by6',1/6)
                else:
                    self.encode720pvideo('720p1by10',1/10)
                    self.encode480pvideo('480p1by10',1/10)
            elif(self.quality_of_file == 576 or self.quality_of_file == 480):
                if(self.lensec<=1200):
                    self.encode480pvideo('480p1by4',1/4)
                    self.encode360pvideo('360p1by4',1/4)
                elif(self.lensec<=3600):
                    self.encode480pvideo('480p1by6',1/6)
                    self.encode360pvideo('360p1by6',1/6)
                else:
                    self.encode480pvideo('480p1by10',1/10)
                    self.encode360pvideo('360p1by10',1/10)
            elif(self.quality_of_file == 360):
                if(self.lensec <= 1200):
                    self.encode360pvideo('360p1by4',1/4)
                elif(self.lensec<=3600):
                    self.encode360pvideo('360p1by6',1/6)
                else:
                    self.encode360pvideo('360p1by10',1/10)
            else:
                if(self.lensec <=1200):
                    self.encodeothervideo('other1by4',1/4)
                elif(self.lensec<=3600):
                    self.encodeothervideo('other1by6',1/6)
                else:
                    self.encodeothervideo('other1by10',1/10)
            
            self.mpdgeneration()

            self.uploadtos3(self.filenm,
                        self.output_folder+'/'+self.filenm)
            os.remove(self.filenm)
            self.cleanup()
            return self.ret
    
    
        


        
        

            

    
