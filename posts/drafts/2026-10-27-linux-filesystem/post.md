---
publish_at: 2026-10-27 09:00
status: draft
topic: linux
source: my Linux notes (AlmaLinux 9)
formula: F15 Explain-Simply (number-first hook), via linkedin-skills post-writer
alt: Handwritten notes page 1 of 4: the Linux directory tree under / (etc, home, root, var, usr, dev) and absolute vs relative paths. | Page 2 of 4: wildcards (*, ?, [a-g]), brace expansion and redirection operators (>, >>, 2>, &>, <). | Page 3 of 4: reading ls -l, what r, w and x mean on files vs directories, and numeric modes 755, 644, 640. | Page 4 of 4: umask 002 gives 664 not 644, setUID and sticky bits, and three traps: chmod -R 644, cp -r vs cp -a, rm -rf.
---

🐧 Linux: Moving Around the Filesystem

664, not 644.

That's the permission a new file actually gets with umask 002 on AlmaLinux. 644 is the answer people often expect, but the math doesn't hold up: 666 minus 002 is 664.

The filesystem is where all of this lives, and permissions are the part worth slowing down for. So I wrote myself the plain-English version.

🔐 rwx on a file
r = you can read it
w = you can change it
x = you can run it

📁 rwx on a directory
r = you can list the names inside
w = you can create, delete or rename things inside
x = you can enter it with cd

That second list surprises most people. Deleting a file is a directory permission, so a read-only file can still be deleted by anyone with w and x on its folder.

🔢 The numbers are just sums: r=4, w=2, x=1. That makes 755 rwxr-xr-x and 640 rw-r-----.

🎭 umask removes bits from 666 for files and 777 for directories. 002 gives 664 and 775, while 022 gives 644 and 755.

⚠️ One trap to remember: chmod -R 644 on a folder strips x from every subfolder, and nobody can cd into them anymore. chmod -R u=rwX,go=rX keeps directories enterable.

Swipe through the 4 pages of my handwritten notes for everything else: the / tree, paths, wildcards, redirection, ls -l and the traps worth remembering.

P.S. Save this for the next time a terminal tells you "Permission denied".

#Linux #AlmaLinux #RHEL #LinuxAdmin #SysAdmin #Bash #DevOps #OpenSource #LearningInPublic
