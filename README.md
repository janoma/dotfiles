# dotfiles
A set of basic, common settings for my \*nix environment.


## Installation

```sh
git clone https://github.com/janoma/dotfiles ~/.dotfiles
~/.dotfiles/install
```

When you run `vim +BundleInstall +qa` the first time, it will complain that it
doesn't find the `molokai` color scheme. Just ignore the message, since the
corresponding package will be downloaded with that command and be available
afterwards.

### Optional packages
Not needed everywhere, so I install these as I need them. Just keeping them here
as a reminder.

```sh
brew install ant cgdb cmake gcc lame ffmpeg libass libogg libsamplerate libvorbis libvpx maven node nvm openssl watch x264 x265 yarn
```
