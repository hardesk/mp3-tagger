# mp3-tagger
A tool to fixup/change ID3 tags of an mp3 sequence. I wrote this tool to fixup ID3 tags of the audiobooks I've acquired.

Requires eyed3, install with:
```$ pip3 install eyed3```

## Usage

The tool reads a json config file and applies those settings to each file that was passed on the command line in sequence. The config file contains a dictionary of properties mapped to values, keys of which are properties discovered by python's dir command on `eyed3.core.tag` object. So some are questionable, but can list them using -l. It's a good starting point to see what values you want changed/modified. Also passing -a prints all properties and their values, which in turn helps to discover what you'd want to set/change. The values you set can contain a reference, marked in curly braces to any of the properties listed with -l. In addition to those, a few useful properties are synthesized:
- `{file_index}` file index as parsed from the file name (see --rere)
- `{file_name}` file name
- `{inc_index}` number incremented for each file starting from 1

When resolving properties, Python's formatting string can be specified after a colon. So `{file_index:03d}` will print file index in three digits prepending zeroes as necessary.

`$images` is a special property to modify images. Keys are names of images to set and can be discovered using `--list-image-types` option. Usually you want `front_cover`. The data can be specified either as a filename or as a base64 embedded string. The format is "filename:`<mime-type>`:`<file-name>`" or "data:`<mime-type>`:`<base64-image-data>` respectively, for example:

```
"$images": {
	"front_cover": "filename:image/jpeg:ninety-eighty-four-1024.jpg",
	"back_cover": "data:image/png:iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
}
```

Each of the properties can have a regex filter so that the property will only be applied if the filter matches. The syntax is `<property>|<regexp>[|<value-of-property-to-match]` where the last value can be omitted in which case `file-name` will be used, for example:

```
"title|01.*": "first track",
"title|second.*": "track named {file_name}",
"title|03|{file_index}": "the third track"
"title": "track number {file_index}"
```

Filtering allows setting particular properties only to some files.
