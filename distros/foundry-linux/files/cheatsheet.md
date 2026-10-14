# Your Projects folder

Foundry Linux puts your work here. A few things already on the bench:

| To | Run |
| --- | --- |
| See this computer at a glance | `pfetch` or `fastfetch` |
| Find text in every file below here | `rg "some words"` |
| Find a file by name | `fd name` |
| Start a project | `mkdir my-thing && cd my-thing && git init` |
| Keep a terminal session running | `tmux` (detach with Ctrl+B, then D) |
| Get another Linux to build in | `distrobox create --image ubuntu:24.04 --name ubuntu`, then `distrobox enter ubuntu` |
| Watch what is busy | `htop` |

Apps in the menu: Visual Studio Code for code, GIMP and Inkscape for
pictures, Blender for 3D, Firefox for everything else, and Flatseal to see
what each app may reach.

Foundry Linux updates as one image. To get the newest build: `sudo bootc upgrade`,
then restart.
