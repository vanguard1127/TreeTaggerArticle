from .models import Post, Comment, Tag
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import PostForm
from django.views.generic import (
    CreateView,
    ListView,
    DetailView,
    UpdateView,
    DeleteView
)
from .treetagger import treetaggerwrapper
import html2text
import re
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from functools import reduce
import operator

def spacify(value, autoescape=None):
    if autoescape:
        esc = conditional_escape
    else:
        esc = lambda x: x
    return mark_safe(re.sub('\s', '&'+'nbsp;', esc(value)))

class PostListView(ListView):
    model = Post
    template_name = 'blog/index.html'
    context_object_name = 'posts'
    paginate_by = 5

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            keyword = self.request.GET['q']
        except:
            keyword = ''
        #context['keyword'] = keyword
        context['keyword'] = spacify(keyword, True)
        return context

    def get_queryset(self):
        try:
            keyword = self.request.GET['q']
        except:
            keyword = ''

        if (keyword != ''):

            #tag_list = Tag.objects.filter(tag_string__icontains=keyword)\
            #    .select_related('post').values('post_id')
            tag_en_s = get_list_tags_from(keyword, 0)
            tag_ro_s = get_list_tags_from(keyword, 0)
            tags = list()
            query = Q()  # empty Q object
            for tag_en in tag_en_s:
                tags.append(tag_en)
                query |= Q(tag_string__icontains=tag_en)
            for tag_ro in tag_ro_s:
                tags.append(tag_ro)
                query |= Q(tag_string__icontains=tag_ro)
            object_id_lists = set()
            #tag_list = Tag.objects.filter(reduce(operator.or_, (Q(tag_string__contains=x) for x in tags))).select_related('post').values('post_id')
            tag_list = Tag.objects.filter(
                query).select_related('post').values('post_id')
            for tag in tag_list:
                object_id_lists.add(tag['post_id'])
            return self.model.objects.filter(pk__in=object_id_lists)
        else:
            object_list = self.model.objects.all()
            return object_list


class UserPostListView(ListView):
    model = Post
    template_name = 'blog/user_posts.html'
    context_object_name = 'posts'
    paginate_by = 5

    def get_queryset(self):
        user = get_object_or_404(User, username=self.kwargs.get('username'))
        return Post.objects.filter(author=user).order_by('-date_posted')


class PostDetailView(DetailView):
    model = Post


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm

    def form_valid(self, form):
        form.instance.author = self.request.user
        redirect_url = super(CreateView, self).form_valid(form)
        run_treetagger(convertHtmlToText(form.instance.content), 0, form.instance, form.instance.author)
        return redirect_url

class PostUpdateView(LoginRequiredMixin,  UpdateView):
    model = Post
    form_class = PostForm

    def form_valid(self, form):
        form.instance.author = self.request.user
        redirect_url = super(UpdateView, self).form_valid(form)
        run_treetagger(convertHtmlToText(form.instance.content), 0, form.instance, form.instance.author)
        return redirect_url

    def test_func(self):
        post = self.get_object()
        if self.request.user == post.author:
            return True
        return False

def convertHtmlToText(html):
    h = html2text.HTML2Text()
    h.ignore_links = True
    return h.handle(html)

def delete_tags_by_post(postid):
    Tag.objects.filter(post_id=postid).delete()

def run_treetagger(text, lang, post, author):
    delete_tags_by_post(post)
    tagger_lang = 'en'
    if lang == 0:
        tagger_lang = 'en'
    else:
        tagger_lang = 'ro'

    tagger = treetaggerwrapper.TreeTagger(TAGLANG=tagger_lang)
    tags = tagger.tag_text(text)
    if (isinstance(tags, list)) and (len(tags) > 0):
        for tag in tags:
            if tag is not None:
                tag_infos = re.split(r'\t+', tag)
                if len(tag_infos) == 3:
                    try:
                        d_tag = Tag()
                        d_tag.author = author
                        d_tag.post = post
                        d_tag.original = tag_infos[0]
                        d_tag.tag_type = tag_infos[1]
                        d_tag.tag_string = tag_infos[2]
                        d_tag.save()
                    except Exception as err:
                        print(err)

def get_list_tags_from(text, lang):
    tagger_lang = 'en'
    if lang == 0:
        tagger_lang = 'en'
    else:
        tagger_lang = 'ro'
    tagger = treetaggerwrapper.TreeTagger(TAGLANG=tagger_lang)
    tags = tagger.tag_text(text)
    strings = set()
    if (isinstance(tags, list) and (len(tags) > 0)):
        for tag in tags:
            if tag is not None:
                tag_infos = re.split(r'\t+', tag)
                if len(tag_infos) == 3:
                    strings.add(tag_infos[2])
    return strings

class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Post
    success_url = '/'

    def test_func(self):
        post = self.get_object()
        if self.request.user == post.author:
            return True
        return False


def about(request):
    return render(request, 'blog/about.html', {'title': 'About'})


@login_required
def add_comment(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.method == 'POST':
        user = User.objects.get(id=request.POST.get('user_id'))
        text = request.POST.get('text')
        Comment(author=user, post=post, text=text).save()
        messages.success(request, "Your comment has been added successfully.")
    else:
        return redirect('post_detail', pk=pk)
    return redirect('post_detail', pk=pk)
