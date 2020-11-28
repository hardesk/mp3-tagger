#!/usr/bin/env python3

import os
import sys
import re
import eyed3
import eyed3.id3
import json
import argparse
import doctest
import base64

dbg=0

class Config:

    class Template:
        """ Template tests
        >>> t=Config.Template("index is {index:03d} - with {title}")
        >>> t.resolve({ 'index': 10, 'title':'Mustang' })
        'index is 010 - with Mustang'
        >>> t=Config.Template("title")
        >>> t.resolve({})
        'title'
        """

        def __init__(self, templ):
            self.templ=templ

        def resolve(self, props):
            pos=0
            result=""
            if not isinstance(self.templ, str): return self.templ

            for fulltag in re.finditer("({[^}]*})", self.templ):
                tag_m=re.match('{([^}:]*)(?:(:[^}]*))?}', fulltag.group(1))
                tag=tag_m.group(1)
                tag_fmt="{{{}}}".format("" if tag_m.group(2) == None else tag_m.group(2))
                val=props[tag]
                if val == None:
                    print("Unable to find property {}".format(tag));
                    raise KeyError("no tag property {}".format(tag))
                result += self.templ[pos:fulltag.start(1)]
                result += tag_fmt.format(val)
                pos += fulltag.end(1)
            result += self.templ[pos:]
            return result

    class Pic:
        """ Template tests
        >>> img='data:image/png:iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVQYV2NgYAAAAAMAAWgmWQ0AAAAASUVORK5CYII='
        >>> p=Config.Pic(data=img, match="01.*/{file_name}")
        >>> p.does_match( {'file_name':"01.mp3"} )
        True
        >>> p.does_match( {'file_name':"1.mp3"} )
        False
        >>> p.resolve_image_data( {} )
        b'u\\xabZ\\x8af\\xa0{\\xfag\\x82%A9\\x1c4(h(\\x00\\x00\\x005%!\\x11H\\x00\\x00\\x00\\x04\\x00\\x00\\x00\\x04 \\x10\\x00\\x00\\x02\\xd4p0\\x08\\x00\\x00\\x00-%\\x11\\x05Pa]\\x8d\\x81\\x80\\x00\\x00\\x00\\x0c\\x00\\x05\\xa0\\x99d4\\x00\\x00\\x00\\x01%\\x159\\x12\\xb9\\t\\x82\\x08'
        >>> p=Config.Pic('filename:image/jpeg:{file_index}.jpeg')
        >>> p.resolve_image_data( {'file_index': 100} )
        Traceback (most recent call last):
         ...
        FileNotFoundError: [Errno 2] No such file or directory: '100.jpeg'
        """

        def __init__(self, data, match=None):
            # data:mime-type:base64-encoded-data
            # filename:mime-type:file-name
            typ, self.mime, content=data.split(':')
            if typ.lower()=='file' or typ.lower()=='filename':
                self.filename=Config.Template(content)
                self.data=None
            elif typ.lower()=='data':
                self.data=base64.b64decode(data.encode('ascii'))
                self.filename=None
            else:
                self.data=None
                self.filename=None

            self.match=match

        def is_nil(self):
            return self.data==None and self.filename==None

        def does_match(self, props):
            if self.match==None: return True

            r, tmpl=self.match.split('/')
            value=Config.Template(tmpl).resolve(props)
            if self.match==None or re.match(r, str(value)):
                return True
            return False

        def resolve_image_data(self, props):
            if self.data != None:
                return self.data
            resolved_filename=self.filename.resolve(props)
            with open(resolved_filename, 'rb') as f:
                return f.read()

    class Context:
        def __init__(self, opts):
            self.inc_index=1
            self.opts=opts

        def do_delete(self, f, key):
            if dbg>0: print("delete {} for {}".format(key, f.path))
        
        def apply(self, mp3, config):
            if config.tmpl==None: return False

            # pull properties from mp3
            tag_props={ x:getattr(mp3.tag, x) for x in dir(mp3.tag) if x[0]!='_' if not any(c.isupper() for c in x) }

            tag_props['inc_index']=self.inc_index
            m=re.match('\s*(\d+)', os.path.basename(mp3.path))
            tag_props['file_index']=int(m.group(1))
            tag_props['file_name']=os.path.basename(mp3.path)
            tag_props['file_path']=mp3.path
            tag_props['none']=None

            if self.opts.renumber and tag_props['title'] != None:
                tit=tag_props['title']
                titm=re.match(self.opts.rere, tit)
                if titm != None:
                    print("  modify title: {} -> {}".format(tit, titm.group(1)))
                    tag_props['title']=titm.group(1)

            for k in config.tmpl:
                cmd=None
                templ=config.tmpl[k]
                new_data=templ.resolve(tag_props)
                # if we find '(' in data, means it's a tuple and so convert it to actual tuple doing eval
                if isinstance(new_data, str) and '(' in new_data: new_data=eval(new_data)

                print("  {}: {} -> {}".format(k, getattr(mp3.tag, k), new_data))
                if not self.opts.dryrun:
                    setattr(mp3.tag, k, new_data)

            for k in config.images:
                i=config.images[k]
                r, tmpl=i.match.split('/')
                value=Config.Template(tmpl).resolve(tag_props)
                if i.does_match(tag_props):
                    if i.is_nil():
                        mp3.tag.images.remove(k)
                    else:
                        pic_type=eyed3.id3.frames.ImageFrame.stringToPicType(k.upper())
                        imgdat=i.resolve_image_data(tag_props)
                        print("  Setting {} picture {} bytes for {}".format(i.mime, len(imgdat), k))
                        mp3.tag.images.set(pic_type, imgdat, i.mime, "", )

            self.inc_index+=1

    # Config
    def __init__(self):
        self.tmpl={}
        self.images={}

    def read(self, json_file):
        j = json.load(json_file)
        for k in j:
            if k[0]=='$':
                cmd=k[1:]
                dat=j[k]
                if cmd=='images':
                    for pic_type in dat:
                        i=dat[pic_type]
                        self.images[pic_type]=Config.Pic(i['image'], i['match'])
            else:
                self.tmpl[k]=Config.Template(j[k])

def main():

    rere="[\d\W]*(.*)"
    ap=argparse.ArgumentParser()
    ap.add_argument('names', nargs='*', help='ID3 files to prcess')
    ap.add_argument('-n', '--dryrun', action='store_true', help='do not modify files')
    ap.add_argument('-s', metavar='STRING', nargs=1, help='json config as a string')
    ap.add_argument('-c', '--config-file', nargs=1, help='json config file. pass - to read from stdin')
    ap.add_argument('-1', '--keep-v1', action='store_true', help='do not remove v1 tag if present')
    ap.add_argument('-l', '--list-tags', action='store_true', help='list tags that are present')
    ap.add_argument('--list-image-types', action='store_true', help='list possible image types to set')
    ap.add_argument('-a', '--all', action='store_true', help='list all tags/properties that were discovered on id3 object and are potentially accessible')
    ap.add_argument('--renumber', action='store_true', help='renumber title. By default strips number and non-alnum from the beginning.')
    ap.add_argument('--rere', metavar='REGEXP', type=str, nargs=1, default=rere, help='Regexp used to renumber title. It is used to extract title as match.group(1). Default: {}'.format(rere))
    args =ap.parse_args()

    if args.list_image_types:
        [print('{}'.format(x)) for x in dir(eyed3.id3.frames.ImageFrame) if x[0].isupper()]
        return

    config=Config()
    if args.config_file:
        if args.config_file[0] != '-':
            with open(args.config_file[0]) as json_file:
                config.read(json_file)
        else:
            config.read(sys.stdin)
    elif args.s:
        with StringIO(args.config[0]) as json_file:
            config.read(json_file)

    ctx=Config.Context(args)
    for name in args.names:

        if not os.path.isfile(name):
            print("  File {} not found. Skipping".format(name))
            continue

        f=eyed3.load(name)

        if args.list_tags:
            if f.tag:
                print("{} | Available tags, ID3 v1:{} v2:{}".format(name, f.tag.isV1(), f.tag.isV2()))
                tag_props={ x:getattr(f.tag, x) for x in dir(f.tag) if x[0]!='_' if not any(c.isupper() for c in x) }
                for k,v in tag_props.items():
                    if isinstance(v, (str, tuple, int, float)) \
                            or isinstance(v, (eyed3.id3.tag.ImagesAccessor, eyed3.id3.tag.LyricsAccessor)) \
                            or (args.all and not callable(v)):
                        vv=v
                        #if isinstance(v, (eyed3.id3.tag.ImagesAccessor, eyed3.id3.tag.LyricsAccessor)):
                        print("  {}: {}".format(k, vv))
            else:
                print("No available ID3 tags found in {}".format(f.path))
        else:
            print("Processing {}".format(name))

            if f.tag==None:
                f.initTag()
            ctx.apply(f, config)

            if not args.dryrun:
                f.tag.save(version=eyed3.id3.tag.ID3_V2_4)

                if f.tag.isV1() and not args.keep_v1:
                    print("  Removing ID3v1")
                    if not eyed3.id3.tag.Tag.remove(name, version=eyed3.id3.tag.ID3_V1, preserve_file_time=True):
                       print("  Failed to remove ID3v1 from {}".format(name))


if __name__ == "__main__":
    main()


