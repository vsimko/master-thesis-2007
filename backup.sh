#!/bin/sh

DATE=`date +%Y-%m-%d-%H%M`
ARCH="ag-thesis-$DATE.tgz"
ARCH_LOCATION="/home/vlx/$ARCH"

tar cfz "$ARCH_LOCATION" ./
#scp "$ARCH_LOCATION" "vlx@ciant114.cesnet.cz:$ARCH"

echo "
    put '$ARCH_LOCATION' /home/vlx/
    put main.pdf /var/www/agnode/uploads/Thesis/vsimko-thesis.pdf
" | sftp -oPort=52222 vlx@ciant114.cesnet.cz

echo "backup archived to $ARCH_LOCATION."