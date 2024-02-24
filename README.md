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

### Font
Download and install `MesloLGS NF` font from Powerlevel10k.

### Packages I use
```sh
brew install wget dirname trash ripgrep htop ffmpeg nvm openssl zsh-autosuggestions zsh-syntax-highlighting
```

### Optional packages
Not needed everywhere, so I install these as I need them. Just keeping them here
as a reminder.

```sh
brew install lame flac x264 x265 gcc cgdb nginx pyenv
```
