#!/bin/bash

sed -i -e '$a\' predicati.csv
previous_tp=""
counter=0

while IFS=',' read -r line; do
  IFS=',' read -ra elements <<< "$line"

  tp="${elements[0]}"
  tp="${tp#[}"
  tp="${tp%]}"

  if [[ "$tp" == "$previous_tp" ]]; then
    ((counter++))
  else
    counter=1
  fi
  previous_tp="$tp"

  echo "" >&2
  echo "Training with $tp as target predicate" >&2

  tp_name="${tp##*/}_$counter"

  ip_args=""
  for (( i=1; i<${#elements[@]}; i++ )); do
    ip_args+="-ip ${elements[i]} "
  done

  mkdir -p "experiments/training/$tp_name"

  for i in {1..4}; do
    echo "Experiment $i" >&2
    for model in uniform frequency inverse-frequency fit; do
      echo "Model: $model" >&2
      for d in {1..4}; do
        echo "Degree: $d" >&2
        python train.py \
          -m "$model" \
          -i resources/data.ttl \
          -tp "$tp" \
          $ip_args \
          --device "cuda:0" \
          -d "$d" \
          -it 300 \
          -o "experiments/training/$tp_name/$model.d$d.exp$i.json"
      done
    done
  done
  
  bash report.sh "experiments/training/$tp_name/.report" $tp

done < predicati.csv


