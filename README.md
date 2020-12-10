# mp3-tagger
A tool to fixup/change ID3 tags of an mp3 sequence. I wrote this tool to fixup ID3 tags of audiobooks I've acquired.


Requires eyed3, install with:
```$ pip3 install eyed3```

## Usage

The tool reads a json config file and applies those settings to each file that was passed on the command line in sequence. The config file contains a dictionary of properties mapped to values. Keys of the dictinary are `eyed3.core.tag` properties discovered by python's dir command. You can list the ones with values using -l. It's a good starting point to see what values you want changed/modified. Also passing -a prints all properties. It in turns helps to discover what you'd want to set also.

$images is a special property for a dictionary of images. Keys to the dictionary can be discovered using `--list-image-types` option. Usually you want `front_cover`. Image can be specified either as a filename or as a base64 embedded data. The format is "filename:`<mime-type>`:`<file-name>`" or "data:`<mime-type>`:`<base64-image-data>` respectively, for example:
```"$images": {
	"front_cover": "filename:image/jpeg:ninety-eighty-four-1024.jpg",
	"back_cover": "data:image/png:iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
}
```

Each of the properties can have a regex filter. The property will only be applies if the filter matches. The syntax is `<property>:<regexp>[:<value-of-property-to-match], for example:
```"title|01.*": "first track",
"title|second.*": "second track",
"title|03|{file_index}": "second track"```

