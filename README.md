dotfiles
========
A set of basic, common settings for my \*nix environment.

vim
---
Includes [YouCompleteMe](https://github.com/Valloric/YouCompleteMe), [a](https://github.com/vim-scripts/a.vim), [vim-sensible](https://github.com/tpope/vim-sensible), [vundle](https://github.com/gmarik/Vundle.vim) and [Toggle](https://github.com/vim-scripts/Toggle).

tmux
---
Color settings, status bar, plus some bindings, many of which I still don't use :(

bash
----
`.bash_profile` and the like, including my beloved aliases.

Installation
=======
    git clone https://github.com/janoma/dotfiles ~/.dotfiles
    ln -s ~/.dotfiles/vim/vimrc ~/.vimrc
    ln -s ~/.dotfiles/tmux/tmux.conf ~/.tmux.conf
    ln -s ~/.dotfiles/bash/bash_profile ~/.bash_profile
