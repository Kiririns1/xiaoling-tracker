# 上传到你自己的 GitHub

## 一、创建空仓库

1. 登录自己的 GitHub，打开 [新建仓库页面](https://github.com/new)。
2. 仓库名建议 `xiaoling-tracker`，填写作品描述。
3. 按赛事要求选择 Public 或 Private；私有仓库需要给裁判账号访问权限。
4. **不要勾选自动添加 README、.gitignore 或许可证**，本地都已准备好。点击 Create repository。

这里不会替你登录或上传。以下命令由你在自己的账号下执行。

## 二、上传解压后的项目目录

本项目包含厂商库与模型，应上传**解压后的文件**。总 ZIP 约数百 MB，不要把总 ZIP 当作一个文件提交进普通 Git 仓库。GitHub 浏览器单文件限制 25 MiB，普通 Git 单文件上限 100 MiB；大型发布包适合 Releases：[GitHub 官方说明](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)。

在本目录（能直接看到 README.md、source、runtime、firmware）打开 PowerShell，先检查：

```powershell
python .\tools\verify_submission.py
git --version
```

把下面的 `你的GitHub用户名` 替换成你自己的用户名，仓库名和刚创建的保持一致：

```powershell
git init -b main
git add .
# 原厂SDK自带的忽略规则会忽略依赖快照；本次提交的source已清空配置且没有build目录。
git add -f source
git commit -m "Release Xiaoling competition submission v3.1.2"
git remote add origin https://github.com/你的GitHub用户名/xiaoling-tracker.git
git push -u origin main
```

首次提交若提示身份未设置，只在当前仓库设置自己的身份，再重跑 commit 和 push：

```powershell
git config user.name "你的GitHub昵称"
git config user.email "你的GitHub已验证邮箱或noreply邮箱"
```

推送时按 Git Credential Manager／浏览器提示登录自己的账号。不要把 GitHub 密码或 Token 写进命令、README 或聊天。

上传前只使用本发布目录；不要把上一级旧固件 ZIP、Flash 备份、个人环境、填好真实凭据的工作副本一起加入。`git add -f source` 只用于这份已检查的空配置源码；配置好自己的私有副本后不要再次照抄该命令上传。

GitHub 官方步骤：[添加本地项目](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github)。

## 三、创建正式 Release

1. 打开仓库的 **Releases → Draft a new release**。
2. 新建标签 `v3.1.2-competition`，Target 选择 `main`。
3. 标题填写“小灵比赛提交版 v3.1.2”。
4. 说明可使用 [RELEASE_NOTES.md](RELEASE_NOTES.md)。
5. 将本次生成的 **`Xiaoling_Competition_Submission_v3.1.2.zip`** 拖入附件区域。
6. 确认不勾选 pre-release，发布 Release。

官方说明：[管理 Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository?tool=webui)。ZIP 放在 Release 附件，不再提交进 source。

## 四、提交给赛事方

仓库地址：`https://github.com/你的GitHub用户名/xiaoling-tracker`

正式发行页：`https://github.com/你的GitHub用户名/xiaoling-tracker/releases/tag/v3.1.2-competition`

查看方式：打开仓库首页 README；在 `source/` 查看源码，`firmware/` 查看空配置固件，`runtime/` 获取电脑端；推荐下载 Release 的完整 ZIP，按 `docs/JUDGE_QUICKSTART.md` 配置并运行。

复制 [赛事提交模板](SUBMISSION_TEMPLATE.md) 并替换用户名、仓库名、参赛队伍信息。仓库尚未实际上传前，这些是地址模板，不能作为已经存在的仓库地址提交。
