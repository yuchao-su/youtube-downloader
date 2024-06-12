from flask import Flask, request, send_file, jsonify, render_template
from pytube import YouTube
from flask_cors import CORS
import os
import time
from urllib.parse import quote
import traceback
import http.client
import pytube.exceptions
from pytube.exceptions import VideoUnavailable
import uuid

app = Flask(__name__)
CORS(expose_headers='Content-Disposition')



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_itags', methods=['POST'])
def get_itags():
    data = request.get_json()
    video_url = data.get('url')
    if not video_url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        yt = YouTube(video_url)
        streams = yt.streams.filter(file_extension='mp4')
        itags = [{'itag': stream.itag, 'resolution': stream.resolution, 'mime_type': stream.mime_type} for stream in streams]
        return jsonify({'itags': itags})
    except VideoUnavailable:
        return jsonify({'error': '视频不可用'}), 404
    except Exception as e:
        print(f"发生异常: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/download', methods=['POST'])
def download_video():
    data = request.get_json()
    video_url = data.get('url')
    itag = data.get('itag', None)  # 可选的itag参数
    # 打印视频链接和itag日志
    print(f"视频链接: {video_url}, 用户选择itag: {itag}")
    if not video_url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        yt = YouTube(video_url)

        if itag:
            stream = yt.streams.get_by_itag(itag)
        else:
            stream = yt.streams.get_highest_resolution()
        title = yt.title
        # 生成一个有效的文件名，并编码非ASCII字符
        filename = f'{str(uuid.uuid4())}.mp4'
        original_filename = f"{title}.mp4".replace("/", "_").replace("\\", "_")
        encoded_filename = quote(original_filename)

        start_time = time.time()
        output_path = '/Users/bruce/PycharmProjects/pytube/videos'
        print(f'开始下载: {output_path}/{filename}, 视频原名:{original_filename}')
        try:
            stream.download(filename=filename, output_path=output_path)
        except (http.client.IncompleteRead, pytube.exceptions.RegexMatchError, pytube.exceptions.VideoUnavailable) as e:
            try:
                print(f"发生错误: {e}, 1s后重试...")
                time.sleep(1)
                stream.download(filename=filename, output_path=output_path)
            except (http.client.IncompleteRead, pytube.exceptions.RegexMatchError, pytube.exceptions.VideoUnavailable) as e:
                try:
                    print(f"发生错误: {e}, 2s后重试...")
                    time.sleep(2)
                    stream.download(filename=filename, output_path=output_path)
                except (http.client.IncompleteRead, pytube.exceptions.RegexMatchError, pytube.exceptions.VideoUnavailable) as e:
                    print(f"发生错误: {e}, 3s后重试...")
                    time.sleep(3)
                    stream.download(filename=filename, output_path=output_path)

        end_time = time.time()
        download_time = end_time - start_time

        print(f"视频下载完成, 下载耗时: {download_time:.2f} 秒, 实际itag:{stream.itag} 视频名称:{original_filename}")

        response = send_file(output_path + os.path.sep + filename, as_attachment=True)
        response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{encoded_filename}"
        return response
    except Exception as e:
        print(f'发生异常: {e}')
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        try:
            os.remove(output_path + os.path.sep + filename)
            print(f"文件 {filename} 已删除")
        except Exception as error:
            print(f"删除文件 {filename} 时出错: {error}")


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
