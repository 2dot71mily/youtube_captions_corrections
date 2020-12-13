#!/bin/bash
channels='3Blue1Brown Alfredo_Canziani Aurélien_Géron DeepMind Jeremy_Howard Khan_Academy Luis_Serrano minutephysics nature_video Pieter_Abbeel stanfordonline TED Veritasium Weights_&_Biases'
for channel in $channels
do
    python src/postprocess_data.py -c $channel
done
echo All done
