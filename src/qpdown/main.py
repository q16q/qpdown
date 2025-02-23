import argparse, sys, requests, colorlog, tqdm, colorama, os, subprocess

FFMPEG_HWACCEL_ARGS = [] # <- edit this to add hardware acceleration in ffmpeg (google the args for your os and gpu)

# -- args
parser = argparse.ArgumentParser('qpDown')
parser.add_argument('-i', '--input', action = 'store', required = True)
parser.add_argument('-o', '--output', action = 'store', required = True)
arguments = parser.parse_args(sys.argv[1:])

# -- logging
handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s[%(asctime)s] %(name)s :%(levelname)s: %(message)s'))

logger = colorlog.getLogger('qpDown')
logger.setLevel(colorlog.INFO)
logger.addHandler(handler)

# -- ffmpeg check
which = 'where' if os.name == 'nt' else 'which'
output = subprocess.run([which, 'ffmpeg'], capture_output = True, text = True).stdout.strip('\n')
if len(output) < 1:
    logger.fatal('please install ffmpeg :(')
    sys.exit(1) 

# -- core functions
def request(url: str, method: str = 'GET', **kwargs):
    r = requests.request(method, url, **kwargs)
    r.raise_for_status()
    return r

# -- m3u8 parse errors
class NotAPlaylistError(Exception): pass
class InvalidPlaylistStructure(Exception): pass
class InvalidPlaylistType(Exception): pass

# -- m3u8 functions
def get_playlist_type(content: str) -> str:
    if not content.startswith('#EXTM3U'):
        raise NotAPlaylistError('content does not have m3u header!')
    
    if '#EXT-X-STREAM-INF' in content:
        return 'master'
    
    if '#EXTINF' in content:
        return 'segment'

def get_resolutions(content: str): # only for master playlists!
    stream_infs = list(filter(lambda line: '#EXT-X-STREAM-INF' in line, content.splitlines()))
    
    if len(stream_infs) < 1:
        raise InvalidPlaylistType('stream type was detected incorrectly!')
    
    stream_infs = [x.replace('#EXT-X-STREAM-INF:', '') for x in stream_infs]
    
    try:
        return [dict(map(lambda j: j.split('='), x.split(','))) for x in stream_infs]
    except ValueError:
        raise InvalidPlaylistStructure('stream info\'s structure is not correct!')

def get_resolution_url(content: str, resolution: dict) -> str:
    lines = content.splitlines()
    built_res = ','.join(list(map(lambda p: '='.join(p), list(resolution.items()))))
    url_index = lines.index(list(filter(lambda x: built_res in x, lines))[0]) + 1
    return lines[url_index]

def get_segment_urls(content: str, ts_base_path: str) -> str: # only for segment playlists!
    urls = []
    lines = content.splitlines()
    for n, line in enumerate(lines):
        if '#EXTINF:' in line:
            urls.append(ts_base_path + lines[n + 1])
    return urls

# -- ffmpeg functions
def get_hwaccel_params():
    accel_methods = subprocess.run(['ffmpeg', '-hwaccels'], text = True, capture_output = True).stdout.strip('\n')
    if 'cuda' in accel_methods: # nvidia support (looking forward to add more gpus support for different oses)
        return ['-hwaccel', 'cuda']
    else:
        return [] # disable hwaccel

# -- main script
def main_script():
    if not arguments.input.startswith('http'):
        logger.fatal('input is not a link!')
        return 1
    
    try:
        if os.path.exists(arguments.output + '.ts'):
            os.remove(arguments.output + '.ts')
        output_ts = open(arguments.output + '.ts', 'ab')
    except OSError:
        logger.fatal('invalid output path! (non-correct syntax)')
        return 1
    
    logger.info('getting playlist...')
    playlist = request(arguments.input).text
    
    try:
        playlist_type = get_playlist_type(playlist)
    except NotAPlaylistError as e:
        logger.fatal(e)
        return 1
    
    ts_base_path = '/'.join(arguments.input.split('/')[:-1]) + '/'
    
    logger.info('detected playlist to be %s' % playlist_type)
    if playlist_type == 'master':
        try:
            resolutions = get_resolutions(playlist)
        except (InvalidPlaylistType, InvalidPlaylistStructure) as e:
            logger.fatal(e)
            return 1

        if len(resolutions) > 1:
            while True:
                print(colorama.Fore.BLUE + 'select your preferred resolution:')
                for n, res in enumerate(resolutions):
                    print(n, ':', res['RESOLUTION'])
                preferred_res = int(input('[?]: '))
                try:
                    preferred_res = resolutions[preferred_res]
                    break
                except:
                    logger.error('invalid resolution!')
                    print(colorama.Fore.BLUE, end = '')
            print(colorama.Style.RESET_ALL, end = '')
        else:
            preferred_res = resolutions[0]
        
        logger.info('getting segment playlist...')
        segment_playlist_url = get_resolution_url(playlist, preferred_res)
        playlist = request(segment_playlist_url).text
        ts_base_path = '/'.join(segment_playlist_url.split('/')[:-1]) + '/'
    
    segment_urls = get_segment_urls(playlist, ts_base_path)
    logger.info('got %s segments' % len(segment_urls))

    for url in tqdm.tqdm(segment_urls, desc = "merging segments...", total = len(segment_urls), unit = 'step'):
        output_ts.write(request(url).content)
    
    logger.info('converting .ts file to .%s' % arguments.output.split('.')[-1])
    hwaccel_params = get_hwaccel_params()
    logger.info('using hwaccel_params: %s' % hwaccel_params)
    ffmpeg_args = ['ffmpeg', '-hide_banner'] + hwaccel_params + ['-i', output_ts.name, '-vcodec', 'copy', '-acodec', 'copy', '-map', '0:v', '-map', '0:a', arguments.output]
    logger.info('final ffmpeg args: %s' % ffmpeg_args)
    subprocess.run(ffmpeg_args)
    
    output_ts.close()
    if os.path.exists(output_ts.name):
        logger.info('removing the .ts file...')
        os.remove(output_ts.name)
    logger.info('done!')
        
if __name__ == '__main__':
    sys.exit(main_script())