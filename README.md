dotfiles
========
A set of basic, common settings for my \*nix environment.

vim
---
Includes [a](https://github.com/vim-scripts/a.vim), [vim-sensible](https://github.com/tpope/vim-sensible), [vundle](https://github.com/gmarik/Vundle.vim) and [Toggle](https://github.com/vim-scripts/Toggle).

tmux
---
Color settings, status bar, plus some bindings, many of which I still don't use :(

bash
----
`.bash_profile` and the like, including my beloved aliases.

git
---
`.gitconfig` with settings for color, a few aliases, and my username and email.
Replace for your own data if you ever clone this.

Installation
=======

```
git clone https://github.com/janoma/dotfiles $HOME/.dotfiles
$HOME/.dotfiles/install
```

When you run `vim +BundleInstall +qa` the first time, it will complain that it
doesn't find the `molokai` color scheme. Just ignore the message, since the
corresponding package will be downloaded with that command and be available
afterwards.
