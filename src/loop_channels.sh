#!/bin/bash
channels='Luis_Serrano DeepMind Jeremy_Howard'
for channel in $channels
do
    python src/postprocess_data.py -c $channel
done
echo All done
