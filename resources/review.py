from datetime import datetime
from flask import request
from flask_jwt_extended import create_access_token, get_jwt, get_jwt_identity, jwt_required
from flask_restful import Resource
import requests
from config import Config
from mysql_connection import get_connection
from mysql.connector import Error
from email_validator import validate_email, EmailNotValidError
from utils import check_password, hash_password
from datetime import datetime
import boto3
import json



class ReviewListResource(Resource) :

    # 리뷰 생성 API
    @jwt_required()
    def post(self, hotelId) :

        # photo : file
        # content : text
        # rating : text

        user_id=get_jwt_identity()

        if 'photo' not in request.files or 'content' not in request.form :
            return {'error':'데이터를 정확히 보내세요.'},400
        
        file=request.files['photo']
        content=request.form['content']
        rating = request.form['rating']
        # 레이팅 형변환
        rating=float(rating)

        if 'image' not in file.content_type :
            return {'error':'이미지 파일만 올려주세요'},400
        
        # 파일명을 유니크하게 만드는 방법
        current_time=datetime.now()
        new_file_name=current_time.isoformat().replace(':','_') + file.content_type.split('/')[-1]

        file.filename = new_file_name

        # S3에 파일을 업로드
        client=boto3.client('s3',
                    aws_access_key_id = Config.ACCESS_KEY ,
                    aws_secret_access_key = Config.SECRET_ACCESS)
        
        try :
            client.upload_fileobj(file,Config.S3_BUCKET,new_file_name,
                                    ExtraArgs ={'ACL':'public-read','ContentType':file.content_type})
            
        except Exception as e :
            return {'error':str(e)}, 500
        
        # 저장된 사진의 imgUrl 생성
        imgUrl = Config.S3_LOCATION+new_file_name

        # # 문서 요약 API ( 리뷰 요약 )


        # headers = {

        #     "X-NCP-APIGW-API-KEY-ID": Config.client_id,
        #     "X-NCP-APIGW-API-KEY": Config.client_secret,
        #     "Content-Type": "application/json"
        # }
        # language = "ko"

        

        # url= "https://naveropenapi.apigw.ntruss.com/text-summary/v1/summarize" 

        # summaryData = {"document":{
        #     "content":content},
        #     "option":{
        #     "language":language
        #     }
        # }

        # print(json.dumps(summaryData, indent=4, sort_keys=True))

        # response = requests.post(url, data=json.dumps(summaryData), headers=headers)

        # # rescode = response.status_code
        # # print(response)
        # # print(rescode)

        # json_data = json.loads(response.text)
        
        

        # if 'summary' in json_data:
        #     summary = json_data['summary']
        #     print(summary)
        # else:
        #     print("Failed to get summary data")
        #     summary = ""  # 초기화 코드 추가

        


        # DB에 저장


        try :
            connection = get_connection()
            query='''insert into reviews
                    (hotelId,userId,content,rating,imgUrl)
                    values(%s,%s,%s,%s,%s);'''
            record = (hotelId,user_id,content,rating,imgUrl)
            cursor = connection.cursor()
            cursor.execute(query,record)
            connection.commit()
            cursor.close()
            connection.close()

        except Error as e :
            print(e)
            cursor.close()
            connection.close()
            return{'error':str(e)},500
        
        return {'result':'success'},200

    # 특정 호텔에 대한 리뷰 가져오는 API
    # 유저의 name과 user의 프로필 사진 + 리뷰 테이블의 데이터
    @jwt_required()
    def get(self, hotelId) :
        
        offset = request.args.get('offset')
        limit = request.args.get('limit')
        
        try :
            connection = get_connection()

            query = '''select r.*,u.name,u.userImgUrl
                    from reviews r
                    left join user u
                    on u.id = r.userId
                    where r.hotelId = %s
                    order by createdAt desc
                    limit ''' + offset + ''' , ''' + limit + ''' ; '''
            record = (hotelId,)

            ## 중요!!!! select 문은 
            ## 커서를 가져올 때 dictionary = True로 해준다
            cursor = connection.cursor(dictionary=True)

            cursor.execute(query,record)

            resultList=cursor.fetchall()

            i = 0
            for row in resultList :
                resultList[i]['createdAt']=row['createdAt'].isoformat()
                resultList[i]['updatedAt']=row['updatedAt'].isoformat()
                i = i+1


            # print(result_list)

            cursor.close()
            connection.close()
        except Error as e :
            print(e)
            cursor.close()
            connection.close()
            return{"result":"fail","error":str(e)}, 500
        
        return {"result" : 'success','items':resultList,'count':len(resultList)}, 200


    # 리뷰 수정 API
    @jwt_required()
    def put(self, hotelId) :

        # photo : file
        # content : text
        # rating : text

        user_id=get_jwt_identity()

        if 'photo' not in request.files or 'content' not in request.form :
            return {'error':'데이터를 정확히 보내세요.'},400
        
        file=request.files['photo']
        content=request.form['content']
        rating = request.form['rating']
        # 레이팅 형변환
        rating=int(rating)

        if 'image' not in file.content_type :
            return {'error':'이미지 파일만 올려주세요'},400
        
        # 파일명을 유니크하게 만드는 방법
        current_time=datetime.now()
        new_file_name=current_time.isoformat().replace(':','_') + file.content_type.split('/')[-1]

        file.filename = new_file_name

        # S3에 파일을 업로드
        client=boto3.client('s3',
                    aws_access_key_id = Config.ACCESS_KEY ,
                    aws_secret_access_key = Config.SECRET_ACCESS)
        
        try :
            client.upload_fileobj(file,Config.S3_BUCKET,new_file_name,
                                    ExtraArgs ={'ACL':'public-read','ContentType':file.content_type})
            
        except Exception as e :
            return {'error':str(e)}, 500
        
        # 저장된 사진의 imgUrl 생성
        imgUrl = Config.S3_LOCATION+new_file_name

        # DB에 저장

        try :
            connection = get_connection()
            query='''update reviews
                    set
                    content = %s,
                    rating = %s,
                    imgUrl = %s
                    where userId=%s and hotelId = %s;'''
            record = (content,rating,imgUrl,user_id,hotelId)
            cursor = connection.cursor()

            # 트랜잭션 시작
            connection.begin() 

            cursor.execute(query,record)
            connection.commit()
            cursor.close()
            connection.close()

        except Error as e :

            # 트랜잭션 롤백
            connection.rollback()

            print(e)
            cursor.close()
            connection.close()
            return{'error':str(e)},500
        
        return {'result':'success'},200

    # 리뷰 삭제 API
    @jwt_required()
    def delete(self, hotelId) :

        user_id=get_jwt_identity()

        try :
            connection = get_connection()
            query = '''delete  from reviews
                    where userId = %s and hotelId = %s;'''
            record = (user_id,hotelId)

            cursor = connection.cursor()

            connection.begin()

            cursor.execute(query,record)

            connection.commit()

            cursor.close()
            connection.close()
        except Error as e :

            # 트랜잭션 롤백
            connection.rollback()
            
            print(e)
            cursor.close()
            connection.close()
            return{'result':'fail','error':str(e)}, 500

        return {'result':'success'},200
    


# 내 리뷰 조회
class MyReviewCheckResource(Resource):
    
    @jwt_required()
    
    def get(self):
        userId = get_jwt_identity()
        offset = request.args.get('offset')
        limit = request.args.get('limit')

        try :
            connection = get_connection()

            query = '''select r.*, h.title, u.name, u.userImgUrl
                    from reviews r
                    left join hotel h on h.id = r.hotelId
                    left join `user` u on u.id = r.userId
                    where userId = %s
                    order by createdAt desc
                    limit ''' + offset + ''' , ''' + limit + ''' 
                    ; '''
            
            record = (userId,)

            ## 중요!!!! select 문은 
            ## 커서를 가져올 때 dictionary = True로 해준다
            cursor = connection.cursor(dictionary=True)

            cursor.execute(query,record)

            resultList=cursor.fetchall()
            
            i = 0
            for row in resultList :
                resultList[i]['createdAt']=row['createdAt'].isoformat()
                resultList[i]['updatedAt']=row['updatedAt'].isoformat()
                i = i+1
            # print(result_list)

            cursor.close()
            connection.close()
        except Error as e :
            print(e)
            cursor.close()
            connection.close()
            return{"result":"fail","error":str(e)}, 500
        
        return {"result" : 'seccess','items':resultList,'count':len(resultList)}, 200
    

# 요약된 리뷰 가져오기.
class ReviewSummaryResource(Resource):
    @jwt_required()
    
    def get(self,hotelId):

        try :
            connection = get_connection()

            query = '''SELECT content FROM reviews
                    where hotelId=%s;'''
            
            record = (hotelId,)

            ## 중요!!!! select 문은 
            ## 커서를 가져올 때 dictionary = True로 해준다
            cursor = connection.cursor(dictionary=True)

            cursor.execute(query,record)

            resultList=cursor.fetchall()

            contents = [r['content'] for r in resultList]

            all_content = ' '.join(contents)

            print(all_content)
            
            cursor.close()
            connection.close()
        except Error as e :
            print(e)
            cursor.close()
            connection.close()
            return{"result":"fail","error":str(e)}, 500
        
        # 문서 요약 API ( 리뷰 요약 )


        headers = {

            "X-NCP-APIGW-API-KEY-ID": Config.client_id,
            "X-NCP-APIGW-API-KEY": Config.client_secret,
            "Content-Type": "application/json"
        }
        language = "ko"

        

        url= "https://naveropenapi.apigw.ntruss.com/text-summary/v1/summarize" 

        summaryData = {"document":{
            "content":all_content},
            "option":{
            "language":language
            }
        }

        print(json.dumps(summaryData, indent=4, sort_keys=True))

        response = requests.post(url, data=json.dumps(summaryData), headers=headers)

        # rescode = response.status_code
        # print(response)
        # print(rescode)

        json_data = json.loads(response.text)
        
        

        if 'summary' in json_data:
            summary = json_data['summary']
            print(summary)
        else:
            print("Failed to get summary data")
            summary = ""  # 초기화 코드 추가
        
        return {"result" : 'success','summary':summary}, 200
        



