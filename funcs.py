# -*- coding: utf-8 -*-
"""
Created on Thu Apr 28 19:08:05 2016

Read S3 files into memory as a pandas dataframe.
No need to down files onto disk!
The s3 file is opened in binary and can be compressed!

@author: lyin
"""
import os
import fnmatch
import botocore
import boto3

def get_bucket(s3_path):
    '''
    Parses string of the s3_path to return the bucket.
    '''
    bucket_ = s3_path.replace('s3://','').split('/')[0]
    return bucket_

def get_key(s3_path):
    '''
    Parses string of the s3_path to return the key + filename
    '''
    bucket_ = get_bucket(s3_path)
    key_    = s3_path.split(bucket_)[-1][1:]
    return key_

def get_both(s3_path):
    '''
    Parses string of the s3_path to return the (bucket, key + filename)
    '''
    bucket_ =  s3_path.replace('s3://','').split('/')[0]
    key_    = s3_path.split(bucket_)[-1][1:]
    return (bucket_,key_)

    
def disk_2_s3(file,s3_path):  
    '''
    Sends a file in local disk to s3 bucket.
    Please note that the s3_path needs to be this format:
    s3://bucket/key/filename.ext
    '''
        
    # make connection to s3
    s3 = boto3.resource('s3')

    if 's3://' in s3_path:
        '''
        If a full s3 path is given bucket_name is parsed from the user param
        used rather than with the constant from constants.py.
        '''
        bucket_name, key_ = get_both(s3_path)
        bucket = s3.Bucket(bucket_name)
    
    else:
        print("include valid s3:// path")
        return

    # upload file to s3.
    try:
        bucket.upload_file(
            Filename=file,
            Key=key_
        )
    except botocore.exceptions.ClientError as e:
        return "Unexpected error: {err} for pattern '{key}' in {bucket}".format(
                    err=e, key=key_, bucket=bucket_name
                    
            )
    except:
        return "Write Permissions Denied"
    
    
    return "'{f}' loaded to '{path}'".format(f=file, path=s3_path)


def ls(search_key):
    '''
    Inputs ~
    String of an s3 key and file [optional].
    
    Returns either ~
    1) list directory (ls) for all objects in a given bucket or key.
    2) glob-like regex search of files in a given bucket or key
    ''' 
    # create connection
    s3 = boto3.resource('s3')    
    
    if 's3://' in search_key:
        '''
        If a full s3 path is given bucket_name is parsed from the user param
        used rather than with the constant from constants.py.
        '''
        bucket_name, search_key = get_both(search_key)
        bucket = s3.Bucket(bucket_name)
    else:
        print("include valid s3:// path")
        return
    
    # Prase for regex
    root = search_key.replace('s3://','') \
                         .replace(bucket_name,'') \
                         .split('*')
    
    try:
        if len(root) == 1:
            # ls-like list of files in bucket containing the search_key.
            ls = [obj.key for obj in bucket.objects.filter(
                    Prefix=search_key)]
        else:
            # Glob-like regex search for list of files
            ls = fnmatch.filter([obj.key for obj in bucket.objects.filter(
                    Prefix=root[0]) if obj.key != search_key], search_key)
                    
    except botocore.exceptions.ClientError as e:
        return "Unexpected error: {err} for pattern '{key}' in {bucket}".format(
                err=e, key=search_key, bucket=bucket_name)
    
    except KeyError as e:
        return "No files following the pattern '{regex}' found in bucket {bucket}".format(
            regex=search_key, bucket=bucket_name)

    
    return [os.path.join('s3://' + bucket_name, f) for f in ls]

def open(s3_path,encoding="utf-8", bytes=True):
    '''
    Read a file from s3 into a string.
    Can return stream of bytes of string.
    '''
    s3 = boto3.client('s3')

    if 's3://' in s3_path:
        '''
        If a full s3 path is given BUCKET_NAME is parsed from the user param
        used rather than with the constant from constants.py.
        '''
        bucket_, key_ = get_both(s3_path)

    else:
        print("include valid s3:// path")
        return

    try:
        if bytes:
            # returns a stream of bytes
            return s3.get_object(Bucket=bucket_, Key=key_)['Body']
            
        else:
            # reads and decodes stream of bytes
            return s3.get_object(Bucket=bucket_, Key=key_)['Body'] \
                     .read()                                         \
                     .decode(encoding)

    except botocore.exceptions.ClientError as e:
        return "Unexpected error: %s" % e

def read(s3_path, encoding='utf-8', bytes=False):
    '''
    Alias for open()
    '''
    return open(s3_path, encoding, bytes)

def wget(s3_path, local_path=False):
    '''
    Downloads an object within a bucket to local.
    Saves it to working directory unless specified by local_path.
    '''
    s3 = boto3.resource('s3')

    if 's3://' in s3_path:
        '''
        If a full s3 path is given BUCKET_NAME is parsed from the user param
        used rather than with the constant from constants.py.
        '''
        bucket_, key_ = get_both(s3_path)

    else:
        print("include valid s3:// path")
        return

    
    if not local_path:
        local_path = s3_path.split('/')[-1]

    return s3.Object(bucket_, key_).download_file(local_path)

def mv(old_path, new_path, keep=False):
    '''
    Moves a file from one bucket to another.
    '''
    s3 = boto3.client('s3')

    bucket_1, key_1 = get_both(old_path)
    bucket_2, key_2 = get_both(new_path)

    r = s3.copy_object(Bucket=bucket_2, Key=key_2, 
                       CopySource=dict(Bucket=bucket_1, Key=key_1))

    if r['ResponseMetadata']['HTTPStatusCode'] == 200:
        if keep:   
            return r
        else:
            return s3.delete_object(Bucket=bucket_1, Key=key_1)

def cp(old_path, new_path):
    '''
    Alias for mv
    '''
    return mv(old_path, new_path, keep=True)

def rm(s3_path):
    '''
    Removes an object
    '''
    s3 = boto3.client('s3')

    bucket_, key_ = get_both(s3_path)

    return s3.delete_object(Bucket=bucket_, Key=key_)

def remove(s3_path):
    '''
    Alias for rm()
    '''
    return rm(s3_path)

def exists(s3_path):
    '''
    Checks if a key exists.
    '''
    s3 = boto3.resource('s3')    

    bucket_, key_ = get_both(s3_path)

    bucket = s3.Bucket(bucket_)

    objs = list(bucket.objects.filter(Prefix=key_))
    
    if len(objs) > 0 and objs[0].key == key_:
        return True
    else:
        return False