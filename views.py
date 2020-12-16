from django.shortcuts import render,redirect
from django.contrib import messages
from django.views.generic import TemplateView,ListView,DetailView
from .models import Cat,CatImage
import uuid
import boto3
import botocore
import os
import time
# import threading
# import multiprocessing
from PIL import Image
import io


"""
изначально была одна add_photo(...) с boto3 для отсылки to aws
чтобы use threading/multiprocessing you need to have a separ function
,к будет крутить obj class Tread(or Process). так что не пугайся...
note 1: in case of threading...Thread = normal reload with image
note 2: in case of multi..Process your server продолжает работать как конь
+ картинка не перезагружается, так что нужно её вероятно ajax запрашивать
или ещё хуже = перезагружать страницу
"""

def serve_upload(photo,cat_id):
    S3_BASE_URL = f"https://s3-eu-central-1.amazonaws.com/"
    BUCKET ="..."
    file_extention = os.path.splitext(photo.name)[-1]
    key = uuid.uuid4().hex[:6]+file_extention
    s3 = boto3.client('s3')
    s3.upload_fileobj(photo,BUCKET,key)
    url = f"{S3_BASE_URL}{BUCKET}/{key}"
    photo = CatImage(url=url,cat_id=cat_id)
    photo.save()  


def _save_ext(filename):
    file_ext = os.path.splitext(filename)[-1].strip('.').upper()
    return  file_ext in ['JPG', 'JPEG','PNG']           


# TODO: if use exceptions |=> write them into loggs + user re-directs with messages
# otherwise (till now)  no re-direct to the page upload failed
def add_photo(request,cat_id):
    """ attempt to faster upload to the server with a threading"""
    photo = request.FILES.get('photo',None)
    if photo:
        try:
            ext = _save_ext(photo.name)
            if not ext:
                messages.warning(request,"Sorry, this file is not acceptable." )
                return redirect('cats:cat-detail',pk=cat_id)                    
            else:
                img = Image.open(photo)
                size = img.size
                if img.width > 600:
                    print("img too wide",img.width)
                    output_size = (600,600)
                    img.thumbnail(output_size)
                    print("thumbnail done,width:",img.width)
                in_mem_file=io.BytesIO()
                img.convert('RGB').save(in_mem_file,format='JPEG')
                in_mem_file.seek(0)        
                S3_BASE_URL = f"https://s3-eu-central-1.amazonaws.com/"
                BUCKET ="..."
                key = uuid.uuid4().hex[:6] + ".JPEG"
                s3 = boto3.client('s3')
                s3.upload_fileobj(in_mem_file,BUCKET,key)
                url = f"{S3_BASE_URL}{BUCKET}/{key}"
                photo = CatImage(url=url,cat_id=cat_id)
                photo.save()           
                return redirect('cats:cat-detail',pk=cat_id) 
                # Warning ! no redirect because of ongoing multiproccessing
        except botocore.exceptions.ClientError as error:
            if error.response['Error']['Code'] == 'InvalidBucketName':
                messages.warning(request,"Bucket not found." )
            elif error.response['Error']['Code'] == 'LimitExceededException':
                messages.warning(request,"Upload is not longer possible" )
            # logger.warn('API call limit exceeded; backing off and retrying...') 
            # raise error
            return redirect('cats:cat-detail',pk=cat_id)             
        except botocore.exceptions.ParamValidationError as error:
            messages.warning(request,"Wrong params passed." )
            return redirect('cats:cat-detail',pk=cat_id) 
            # raise ValueError('The parameters you provided are incorrect: {}'.format(error))
    else:
        print("file is not attached")
        messages.warning(request,"No file to upload." )
        return redirect('cats:cat-detail',pk=cat_id) 
    return redirect('cats:cat-detail',pk=cat_id)            
        

