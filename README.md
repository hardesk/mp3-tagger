# mp3-tagger
A tool to fixup/change ID3 tags of an mp3 sequence. I wrote this tool to fixup ID3 tags of audiobooks I've acquired.


Requires eyed3, install with:
```$ pip3 install eyed3```

## Usage

The tool reads a json config file and applies those settings to each file that was passed on the command line in sequence. The config file contains a dictionary of properties mapped to values. Keys of the dictinary are `eyed3.core.tag` properties discovered by python's dir command. You can list the ones with values using -l. It's a good starting point to see what values you want changed/modified. Also passing -a prints all properties. It in turns helps to discover what you'd want to set also. The values set can contain a reference to any of the properties listed with -l. A few useful properties are synthesized:
- `{file_index}` file index as parsed from the file name (see --rere)
- `{file_name}` file name
- `{inc_index}` number incremented for each file

When resolving properties, Python's formatting sring can be specified after a colon: `{file_index:03d}` will print file index in three digits prepeding zeroes as necessary.

`$images` is a special property for a dictionary of images. Keys to the dictionary can be discovered using `--list-image-types` option. Usually you want `front_cover`. Image can be specified either as a filename or as a base64 embedded data. The format is "filename:`<mime-type>`:`<file-name>`" or "data:`<mime-type>`:`<base64-image-data>` respectively, for example:

```
"$images": {
	"front_cover": "filename:image/jpeg:ninety-eighty-four-1024.jpg",
	"back_cover": "data:image/png:iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
}
```

Each of the properties can have a regex filter. The property will only be applies if the filter matches. The syntax is `<property>:<regexp>[:<value-of-property-to-match], for example:

```
"title|01.*": "first track",
"title|second.*": "track named {file_name}",
"title|03|{file_index}": "the third track"
"title": "track number {file_index}"
```

Filtering allows to set particular properties only to some files.
