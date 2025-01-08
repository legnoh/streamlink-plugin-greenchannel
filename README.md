# streamlink-plugin-greenchannel

## Install

Copy `greenchannel.py` to [sideload directories](https://streamlink.github.io/cli/plugin-sideloading.html)

```
# macos
mkdir -p "${HOME}/Library/Application Support/streamlink/plugins"
curl -o "${HOME}/Library/Application Support/streamlink/plugins/greenchannel.py" \
    https://raw.githubusercontent.com/legnoh/streamlink-plugin-greenchannel/refs/heads/main/greenchannel.py
```

## Usage

```sh
# play
streamlink "https://sp.gch.jp/" --greenchannel-email="yourmail@test.com" --greenchannel-password="XXX..." best

# play with specified channel
streamlink "https://sp.gch.jp/#ch1" --greenchannel-email="yourmail@test.com" --greenchannel-password="XXX..." best

# get stream url
streamlink "https://sp.gch.jp/#ch1" --greenchannel-email="yourmail@test.com" --greenchannel-password="XXX..." best --stream-url
```
