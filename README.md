# streamlink-plugin-greenchannel

Streamlink plugin for GreenCH.

## Install

Copy `greenchannel.py` to [sideload directories](https://streamlink.github.io/cli/plugin-sideloading.html)

```
# macos
mkdir -p "${HOME}/Library/Application Support/streamlink/plugins"
curl -o "${HOME}/Library/Application Support/streamlink/plugins/greenchannel.py" \
    https://raw.githubusercontent.com/legnoh/streamlink-plugin-greenchannel/refs/heads/main/greenchannel/greenchannel.py
```

## Usage

```sh
# play
streamlink "https://sp.gch.jp/" --greenchannel-email="yourmail@test.com" --greenchannel-password="XXX..." best

# play with specified channel
streamlink "https://sp.gch.jp/#ch1" --greenchannel-email="yourmail@test.com" --greenchannel-password="XXX..." best

# get stream url
streamlink "https://sp.gch.jp/#ch1" --greenchannel-email="yourmail@test.com" --greenchannel-password="XXX..." best --stream-url

# get stream url with low latency option
streamlink "https://sp.gch.jp/#ch1" --greenchannel-email="yourmail@test.com" --greenchannel-password="XXX..." --greenchannel-low-latency best --stream-url
```

## Disclaim

- このプラグインの利用は、すべて自己の責任の元に行ってください。
  - 開発者はこのプラグインの利用によって生じた一切の事案について責任を持ちません。
- 動作を保証するものではありません。
- 怒られたら公開を取りやめます。
