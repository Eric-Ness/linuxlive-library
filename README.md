# The linuxlive Library

Distros people have made with [linuxlive](https://linuxlive.com) and shared.
Each one is a folder in `distros/`. When a pull request adding one is merged,
CI builds it, boot-tests it, and puts the ISO on
[linuxlive.com's Library](https://linuxlive.com/library/) for anyone to
download, no account needed.

## Add your distro

1. Make it first: start from the template
   [Eric-Ness/linuxlive-distro](https://github.com/Eric-Ness/linuxlive-distro)
   (or the wizard on linuxlive.com) and get a green build in your own GitHub.
2. Fork this repository and add one folder, `distros/<slug>/`, where `<slug>`
   is lowercase letters, digits and dashes (3 to 40 characters):

   ```text
   distros/my-distro/
     linuxlive.yaml   your spec, unchanged
     assets/          the wallpaper and logo it names (PNG or JPEG), and a boot
                      splash's .script and PNG images if it has one
     scripts/         its own scripts, if the spec has any (text files)
     files/           files the spec copies into the system, if any
     listing.yaml     how the Library shows it
   ```

   `listing.yaml`:

   ```yaml
   name: My Distro              # as shown on the page
   author: your-github-login    # must be the pull request's author
   tagline: One line, up to 100 characters.
   about: >-
     A few sentences about it, up to 600 characters.
   credits: Where the wallpaper and logo come from, and their licences.
   license: MIT-0               # for your spec and art: MIT-0, MIT, CC0-1.0, CC-BY-4.0 or CC-BY-SA-4.0
   website: https://example.org # optional: your distro's own site, https only
   site_repo: your-github-login/my-distro-site  # optional: that site's repository (see below)
   ```

3. Open a pull request. CI checks the folder and builds and boot-tests your
   distro, as your own build did. A maintainer reviews the art and text, then
   merges.

A distro that runs code of its own (`scripts` or `repos` in its spec) gets a
closer review: CI lists every script and repo in the pull request's check
summary, and a maintainer reads each one before merging, because they run as
root on every computer that installs it. Repos must be public and pinned to a
commit; a pull request that moves a commit is reviewed again.

One distro per pull request; the folder may hold up to 30 MB. To update your
distro, open another pull request changing its folder; to remove it, open one
deleting the folder, or write to abuse@linuxlive.com.

## Your distro's own web site

linuxlive.com publishes each distro's current build at
`https://linuxlive.com/library/<slug>/release.json`: the ISO's size and
SHA-256, its download link, the boot tests and the listing. When a newer
build replaces it, the old build stays downloadable for a week, so a site
that checks once a day never offers a dead link. linuxlive's
[follow-release action](https://github.com/Eric-Ness/linuxlive#follow-a-library-release)
does the checking: run daily in your site's repository, it checks the new
build against the download host and writes it to a file your site's build
reads.

`site_repo` names that repository. linuxlive.com then sends it a
`library-updated` event (a `repository_dispatch` carrying the slug and run)
as soon as it takes a new build, so the site need not wait for its daily run.
It must be a repository of the listing's author, and it only gets the event
if linuxlive.com's token reaches it (for now, the maintainer's own sites);
any other site follows on its daily run.

## Rules

Everything here must follow linuxlive.com's
[rules](https://linuxlive.com/policy/): no malware, nothing illegal, no art
you have no right to share, and no other project's logos or trademarks.
Distros that break them are removed, along with their ISOs.

## Licence

This repository's own files are under MIT No Attribution (see LICENSE). Each
distro's spec and art are under the licence its `listing.yaml` names. The
ISOs contain Ubuntu's or Fedora's packages under their own licences; see
[linuxlive.com/source/](https://linuxlive.com/source/) for their source code.
