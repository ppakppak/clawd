import pathlib, sys, traceback
from google_auth_oauthlib.flow import InstalledAppFlow                                         
                                                                                                  
try:                                                                                           
       CLIENT = pathlib.Path('secrets/client_secret.json')                                        
       TOKEN  = pathlib.Path('secrets/gcal_token.json')                                           
       SCOPES = ['https://www.googleapis.com/auth/calendar']                                      
                                                                                                  
       if not CLIENT.exists():                                                                    
           raise FileNotFoundError(f'{CLIENT} 파일이 없습니다.')                                  
                                                                                                  
       flow = InstalledAppFlow.from_client_secrets_file(CLIENT, SCOPES)                           
       auth_url, _ = flow.authorization_url(prompt='consent')                                     
       print('\n🔗 이 URL을 브라우저에 열어 로그인/허용하세요:\n')                                
       print(auth_url, '\n')                                                                      
       code = input('브라우저가 보여준 승인 코드를 붙여넣고 Enter: ')                             
       flow.fetch_token(code=code)                                                                
                                                                                                  
       TOKEN.write_text(flow.credentials.to_json())                                               
       print('\n✅ OAuth 완료! 토큰 저장 →', TOKEN)                                               
except Exception:                                                                              
       traceback.print_exc()        
