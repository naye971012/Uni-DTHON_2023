import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import wandb
from glob import glob
import os
from torch.utils.data import Dataset, DataLoader
import logging
import sys

from models.models import get_model
from dataloader_class.dataloader import get_loaders
from trainer.trainer import train, test

DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
logger = logging.getLogger(__name__)

def main():
    run = wandb.init()
    configs = CONFIGS(FIXED_CONFIG)

    logger.info("*** data loading ***")
    
    train_loader , val_loader, test_loader = get_loaders(configs)
    
    logger.info(f"Train dataloader size: {len(train_loader)}")
    logger.info(f"Validation datalodaer size: {len(val_loader)}")
    logger.info(f"Test datalodaer size: {len(test_loader)}")


    logger.info("*** model loading***")
    
    init_params = {
        "encoder_name": configs.encoder_name, 
        "encoder_weights": configs.encoder_weights, 
        "classes": configs.classes, 
        "activation": configs.activation
    } 
    model = get_model(configs, architecture=configs.architecture, init_params=init_params)    
    model.to(DEVICE)
    
    if configs.IS_TRAIN:
        logger.info("*** train start ***")
        train(configs, model, train_loader, val_loader)
    
    if configs.IS_TEST:
        logger.info("*** inference start ***")
        test(configs, model, test_loader)
    

        

class CONFIGS:
    """
    DICT 변수를 configs.LR 등의 방법으로 접근하기 위함
    """
    def __init__(self,configs):
        self.configs = configs
    def __getattr__(self, name):
        if name in self.configs:
            return self.configs[name] #here is fixed params
        else:
            return wandb.config.__getattr__(name) #here is bayesian search param

        
if __name__=="__main__":
    
    # Define sweep config
    sweep_configuration = {
        "method": "random", #random or bayes
        "name": "sweep",
        "metric": {"goal": "maximize", "name": "tta_validation_mIOU"},
        "parameters": {
            "epoch": {"value": 25},
            "batch_size": {"value": 13},
            "accumulation_step": {"values": [1,2,4,8]},
            "train_transform": {"values": ['hard_transform']},
    
            "optimizer": {"values": ['sgd', 'adamw','adam','adagrad']},
            "loss": {"value": 'mixed'},
            "lr": {"max": 1e-2, "min": 1e-4},
            "scheduler" : {"values": ["steplr", "reducelronplateau", "sgdr"] },
            
            "encoder_name": {"value": 'resnet101'}, 
            "architecture": {"value": 'DeepLabV3Plus'}, 
            "activation": {"value": None},
            "encoder_weights": {"value": "imagenet"},
            
            "tta": {"value":True}
        },
    }

    # Initialize sweep by passing in config.
    sweep_id = wandb.sweep(sweep=sweep_configuration, project="UNITON_segmentation_sweep")
    
    FIXED_CONFIG = { 
        "IS_TRAIN" : True, 
        "IS_TEST" : False, 
        "SAVE_MODEL" : True, 
        
        'SAVE_DIR' : './predicted_masks',
        'DATA_PATH' : 'segmentation_basis/data',
        'VALI_SIZE' : 0.2,
        "SEED" : 42,
        "RESIZE" : (512,512),
        "NUM_WORKERS" : 8,
        
        "classes": 10
    }
    
    # Start sweep job.
    wandb.agent(sweep_id, function=main, count=4)