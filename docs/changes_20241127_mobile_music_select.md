# 移动端音乐选择界面修改记录 (2024-01-27)

## HTML部分修改

### 修改前
```html
<!-- 移动端音乐选择 -->
<div class="form-group mb-3">
    <select class="form-select" id="musicSelectMobile">
        <option value="">选择音乐文件</option>
    </select>
</div>
```

### 修改后
```html
<!-- 移动端音乐选择 -->
<div class="form-group mb-3">
    <div class="music-list" id="musicListMobile">
        <!-- 音乐列表将通过JavaScript动态填充 -->
    </div>
</div>

<!-- 添加的样式 -->
<style>
.music-list {
    max-height: 200px;
    overflow-y: auto;
    border: 1px solid #dee2e6;
    border-radius: 0.25rem;
    padding: 0.5rem;
}

.music-item {
    padding: 0.5rem;
    margin-bottom: 0.25rem;
    border-radius: 0.25rem;
    cursor: pointer;
    transition: background-color 0.2s;
}

.music-item:hover {
    background-color: #f8f9fa;
}

.music-item.selected {
    background-color: #e9ecef;
    font-weight: bold;
}
</style>
```

## JavaScript部分修改

### 修改前
```javascript
// 加载音乐列表
async function loadMusicList() {
    try {
        const response = await fetch('/get_music_list');
        const data = await response.json();
        
        const musicSelect = document.getElementById('musicSelect');
        const musicSelectMobile = document.getElementById('musicSelectMobile');
        
        // 清空现有选项
        musicSelect.innerHTML = '<option value="">选择音乐文件</option>';
        musicSelectMobile.innerHTML = '<option value="">选择音乐文件</option>';
        
        // 添加音乐选项
        data.music_files.forEach(file => {
            const option = document.createElement('option');
            option.value = file;
            option.textContent = file;
            musicSelect.appendChild(option);
            
            const optionMobile = option.cloneNode(true);
            musicSelectMobile.appendChild(optionMobile);
        });
    } catch (error) {
        console.error('加载音乐列表失败:', error);
    }
}
```

### 修改后
```javascript
// 加载音乐列表
async function loadMusicList() {
    try {
        const response = await fetch('/get_music_list');
        const data = await response.json();
        
        // PC端音乐选择
        const musicSelect = document.getElementById('musicSelect');
        musicSelect.innerHTML = '<option value="">选择音乐文件</option>';
        
        // 移动端音乐列表
        const musicListMobile = document.getElementById('musicListMobile');
        musicListMobile.innerHTML = '';
        
        // 添加音乐选项
        data.music_files.forEach(file => {
            // PC端下拉列表
            const option = document.createElement('option');
            option.value = file;
            option.textContent = file;
            musicSelect.appendChild(option);
            
            // 移动端列表项
            const musicItem = document.createElement('div');
            musicItem.className = 'music-item';
            musicItem.dataset.value = file;
            musicItem.textContent = file;
            musicItem.addEventListener('click', function() {
                // 移除其他项的选中状态
                document.querySelectorAll('.music-item').forEach(item => {
                    item.classList.remove('selected');
                });
                // 添加当前项的选中状态
                this.classList.add('selected');
                // 更新选中的音乐
                selectedMusic = file;
            });
            musicListMobile.appendChild(musicItem);
        });
    } catch (error) {
        console.error('加载音乐列表失败:', error);
    }
}

// 新增：全局变量用于存储选中的音乐
let selectedMusic = '';

// 修改：移动端播放按钮事件
function initMobileControls() {
    // 播放按钮事件
    const playButtonMobile = document.getElementById('playButtonMobile');
    if (playButtonMobile) {
        playButtonMobile.addEventListener('click', function() {
            if (selectedMusic) {
                playMusic(selectedMusic);
            } else {
                alert('请先选择音乐文件');
            }
        });
    }
    
    // ... 其他控制代码保持不变 ...
}
```

## 修改说明

1. HTML修改：
   - 移除了移动端的select元素
   - 添加了新的div容器用于显示音乐列表
   - 添加了相关的CSS样式

2. JavaScript修改：
   - 修改了loadMusicList函数，分别处理PC端和移动端的音乐列表
   - 添加了音乐项的点击事件处理
   - 添加了选中状态的视觉反馈
   - 新增了全局变量selectedMusic用于存储选中的音乐
   - 修改了移动端播放按钮的事件处理逻辑

3. 样式改进：
   - 添加了滚动条支持
   - 添加了悬停效果
   - 添加了选中状态的样式
   - 优化了布局和间距
