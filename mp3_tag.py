#!/usr/bin/env python3

import os
import sys
import re
import eyed3
import eyed3.id3
import json
import argparse
import doctest

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
            tag_props['none']=None

            if self.opts.renumber != None and tag_props['title'] != None:
                tit=tag_props['title']
                titm=re.match(self.opts.renumber, tit)
                if titm != None:
                    print("modify title: {} -> {}".format(tit, titm.group(1)))
                    tag_props['title']=titm.group(1)

            for k in config.tmpl:
                cmd=None
                templ=config.tmpl[k]
                new_data=templ.resolve(tag_props)
                # if we find '(' in data, means it's a tuple and so convert it to actual tuple doing eval
                if '(' in new_data: new_data=eval(new_data)

                print("{}: {} -> {}".format(k, getattr(mp3.tag, k), new_data))
                if not self.opts.dryrun:
                    setattr(mp3.tag, k, new_data)

            self.inc_index+=1

    # Config
    def __init__(self):
        self.tmpl={}

    def load(self, filename):
        with open(filename) as json_file:
            data = json.load(json_file)
            for k in data:
                self.tmpl[k]=Config.Template(data[k])

    def read(self, json_string):
        data = json.loads(json_string)
        for k in data:
            self.tmpl[k]=Config.Template(data[k])


def main():

    ap=argparse.ArgumentParser()
    ap.add_argument('names', nargs='+', help='ID3 files to prcess')
    ap.add_argument('-d', '--dryrun', action='store_true', help='do not modify files')
    ap.add_argument('-c', '--config', nargs=1, help='config')
    ap.add_argument('-f', '--config-file', nargs=1, help='config file. pass - to read it from stdin')
    ap.add_argument('-1', '--keep-v1', action='store_true', help='do not remove v1 tag if present')
    ap.add_argument('--list-tags', action='store_true', help='config file. pass - to read it from stdin')
    ap.add_argument('--renumber', type=str, nargs='?', const="[\d\W]*(.*)", default=None, help='renumber title. By default strips number and non-alnum from the beginning. Optionally pass a regexp to extract title')
    args =ap.parse_args()

    config=Config()
    if args.config_file:
        config.load(args.config_file[0] if args.config_file[0] != '-' else sys.stdin)
    if args.config:
        config.read(args.config[0])

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
                    if isinstance(v, str) or isinstance(v, tuple) or isinstance(v, int) or isinstance(v, float):
                        print("  {}: {}".format(k, v))
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


