import logging
from flask import Flask, redirect, url_for, session, request, render_template
from requests_oauthlib import OAuth2Session
import requests
import time

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

app = Flask(__name__)
app.config['SECRET_KEY'] = '4NupabeEVrCKHEKZR8scG.ozVn9BwcDWkxPANp_Y'

client_id = 'IaSp59idfXJwIXNr4DNv88ExyJCiYzXLHf9oDW8wz9MhNAD8BX'
client_secret = 'cujsbFUnVYFnYBYuAuPn4YB3t9ZQR2y3P7ITlIfej49Ee3LVIO'
authorization_base_url = 'https://www.tumblr.com/oauth2/authorize'
token_url = 'https://api.tumblr.com/v2/oauth2/token'
scope = ['write']

@app.route('/index')
@app.route('/')
def index():
    return render_template('index.html')
    
@app.route('/auth')
def auth():
    tumblr = OAuth2Session(client_id, scope=scope)
    authorization_url, state = tumblr.authorization_url(authorization_base_url, access_type='offline')
    session['oauth_state'] = state
    return redirect(authorization_url)

@app.route('/callback')
def callback():
    tumblr = OAuth2Session(client_id, state=session['oauth_state'])
    token = tumblr.fetch_token(token_url, client_secret=client_secret, authorization_response=request.url)
    session['oauth_token'] = token
    return redirect(url_for('block'))

@app.route('/logout')
def logout():
    session.pop('blog', None)
    session.pop('oauth_token', None)
    session.pop('oauth_state', None)
    return redirect(url_for('index'))

@app.route('/block', methods=['GET', 'POST'])
def block():
    if not session.get('oauth_token', None):
        return redirect(url_for('index'))
    selected_blog = session.get('blog', None)
    if request.method == 'POST':
        blogs = request.form['blogs'].split('\n')
        clean_blogs = []
        for blog in blogs:
            clean_blog = blog.strip()
            if clean_blog and clean_blog not in clean_blogs and clean_blog != "":
                clean_blogs.append(clean_blog.strip())
        print(f'trying to block {len(clean_blogs)} blog(s)')
        results = []
        for blog_group in chunker(clean_blogs, 50):
            result = block_blogs(selected_blog, blog_group)
            # stay in 60 per minute limit
            time.sleep(1.1)
            results.append((blog_group, result))
        return render_template('results.html', results=results)
    # If GET then check if we selected a blog
    if selected_blog:
        return render_template('block.html', blog=selected_blog)
    # we have to get the list of users blogs and let them select one
    blog_list, error = get_blog_list()
    return render_template('select_blog.html', blogs=blog_list, error=error)

@app.route('/set_blog', methods=['GET'])
def set_blog():
    blog = request.args.get('blog')
    session['blog'] = blog
    return redirect(url_for('block'))

def get_blog_list():
    url = f'https://api.tumblr.com/v2/user/info'
    headers = {'Authorization': 'Bearer ' + session['oauth_token']['access_token']}
    response = requests.get(url, headers=headers, timeout=3)
    if response.status_code != 200:
        print(f'Error getting blog list: {response.status_code} {response.text} {response.reason}')
        return [], response.text
    blog_list = [blog['name'] for blog in response.json()['response']['user']['blogs']]
    print(blog_list)
    return blog_list, None

def block_blogs(my_blog, blogs):
    blog_list = ",".join(blogs)
    url = f'https://api.tumblr.com/v2/blog/{my_blog}/blocks/bulk'
    headers = {'Authorization': 'Bearer ' + session['oauth_token']['access_token']}
    data = {'blocked_tumblelogs': blog_list}
    response = requests.post(url, headers=headers, data=data, timeout=10)
    return response.status_code == 200

def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))

if __name__ == '__main__':
    app.run(host="127.0.0.1", port=8080, debug=True)
