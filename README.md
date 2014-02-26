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

git
---
`.gitconfig` with settings for color, a few aliases, and my username and email.
Replace for your own data if you ever clone this.

Installation
=======
With symbolic links
-------------------
    git clone https://github.com/janoma/dotfiles ~/.dotfiles
    ln -si ~/.dotfiles/vim/vimrc ~/.vimrc
    ln -si ~/.dotfiles/tmux/tmux.conf ~/.tmux.conf
    ln -si ~/.dotfiles/bash/bash_profile ~/.bash_profile
    ln -si ~/.dotfiles/git/gitconfig ~/.gitconfig
    vim +BundleInstall +qa

With copies of the originals
----------------------------
    git clone https://github.com/janoma/dotfiles ~/.dotfiles
    cp -i ~/.dotfiles/vim/vimrc ~/.vimrc
    cp -i ~/.dotfiles/tmux/tmux.conf ~/.tmux.conf
    cp -i ~/.dotfiles/bash/bash_profile ~/.bash_profile
    cp -i ~/.dotfiles/git/gitconfig ~/.gitconfig
    vim +BundleInstall +qa
