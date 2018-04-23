# radipy
Radipy is CLI radiko Downloader written by python3.

# Usage

```
$ python radipy.py --help
Usage: radipy.py [OPTIONS]

  Radipy is CLI radiko Downloader written by python3.

Options:
  -a, --area  print station id & name in your area
  -ls         print program titles & start time. using with -id option
  -id TEXT    set station id
  -ft TEXT    set start datetime str formated by yyyyMMddHHmm e.g. 201804171830
  --clear     clear authkey and player in tmp dir
  --help      Show this message and exit.
```

## Example
```
$ python radipy.py --area
create playerFile...
create KeyFile...
access auth1_fms...
generate particleKey...
access auth2_fms...
--------------------------
authentication success.
area_id: JP20
+------------------+--------------------+
|  id              |  名前              |
+------------------+--------------------+
|  SBC             |  SBCラジオ         |
|  RN1             |  ラジオNIKKEI第1   |
|  RN2             |  ラジオNIKKEI第2   |
|  FMN             |  ＦＭ長野          |
|  HOUSOU-DAIGAKU  |  放送大学          |
+------------------+--------------------+

$ python radipy.py -id=RN1 -ls
playerFile already exists.
keyfile already exists.
access auth1_fms...
generate particleKey...
access auth2_fms...
--------------------
authentication success.
area_id: JP20
20180423050000 番組休止中
20180423065500 開始アナウンス
// ...
20180423230000 Music Together
20180424000000 番組休止中


$ python radipy.py -id=SBC -ft=20170319233000
access auth1_fms...
generate particleKey...
access auth2_fms...
--------------------------
authentication success.
area_id: JP20
+----------------------------+
|           title            |
+----------------------------+
|  水樹奈々スマイルギャング  |
+----------------------------+
Now Downloading.../finish!%
```

# requirements

```
pip install -r requirements.txt
```

Using pipenv:

```
pipenv install
```

```
brew install ffmpeg swftools
```

# Tested

+ MacOS 10.13.3
+ Python 3.6.4
+ Pipenv 11.9.0
+ Homebrew 1.6.0c
