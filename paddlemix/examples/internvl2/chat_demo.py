# Copyright (c) 2024 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import paddle
import paddle.vision.transforms as T
from PIL import Image

from paddlemix.models.internvl2.internlm2 import InternLM2Tokenizer
from paddlenlp.transformers import AutoTokenizer, Qwen2Tokenizer, LlamaTokenizer, Llama3Tokenizer
from paddlemix.models.internvl2.internvl_chat import InternVLChatModel
from paddlemix.datasets.internvl_dataset import dynamic_preprocess

paddle.set_grad_enabled(False)

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


def build_transform(input_size):
    MEAN, STD = IMAGENET_MEAN, IMAGENET_STD
    transform = T.Compose([
        # T.Lambda(lambda img: img.convert('RGB') if img.mode != 'RGB' else img),
        T.Resize((input_size, input_size), interpolation='bicubic'),
        T.ToTensor(),
        T.Normalize(mean=MEAN, std=STD)
    ])
    return transform


def load_image(image_file, input_size=448, max_num=12):
    image = Image.open(image_file).convert('RGB')
    transform = build_transform(input_size=input_size)
    images = dynamic_preprocess(image, image_size=input_size, use_thumbnail=True, max_num=max_num)
    pixel_values = [transform(image) for image in images]
    pixel_values = paddle.stack(pixel_values)
    return pixel_values


def load_tokenizer(model_size, model_path):
    if model_size in ['1B']:
        tokenizer = Qwen2Tokenizer.from_pretrained(model_path)
        # TODO:
        tokenizer.added_tokens_encoder =  {'<|endoftext|>': 151643, '<|im_start|>': 151644, '<|im_end|>': 151645, '<img>': 151646, '</img>': 151647, '<IMG_CONTEXT>': 151648, '<quad>': 151649, '</quad>': 151650, '<ref>': 151651, '</ref>': 151652, '<box>': 151653, '</box>': 151654}
        tokenizer.added_tokens_decoder = {v: k for k, v in tokenizer.added_tokens_encoder.items()}

    elif model_size in ['2B', '8B', '26B']:
        tokenizer = InternLM2Tokenizer.from_pretrained(model_path)
        # TODO:
        tokenizer.added_tokens_encoder = {'<unk>': 0, '<s>': 1, '</s>': 2, '<|plugin|>': 92538, '<|interpreter|>': 92539, '<|action_end|>': 92540, '<|action_start|>': 92541, '<|im_end|>': 92542, '<|im_start|>': 92543, '<img>': 92544, '</img>': 92545, '<IMG_CONTEXT>': 92546, '<quad>': 92547, '</quad>': 92548, '<ref>': 92549, '</ref>': 92550, '<box>': 92551, '</box>': 92552}
        tokenizer.added_tokens_decoder = {v: k for k, v in tokenizer.added_tokens_encoder.items()}

    elif model_size in ['4B']:
        tokenizer = LlamaTokenizer.from_pretrained(model_path)
        # TODO:
        tokenizer.added_tokens_encoder = {'<unk>': 0, '<s>': 1, '</s>': 2, '<|endoftext|>': 32000, '<|assistant|>': 32001, '<|placeholder1|>': 32002, '<|placeholder2|>': 32003, '<|placeholder3|>': 32004, '<|placeholder4|>': 32005, '<|system|>': 32006, '<|end|>': 32007, '<|placeholder5|>': 32008, '<|placeholder6|>': 32009, '<|user|>': 32010, '<img>': 32011, '</img>': 32012, '<IMG_CONTEXT>': 32013, '<quad>': 32014, '</quad>': 32015, '<ref>': 32016, '</ref>': 32017, '<box>': 32018, '</box>': 32019}
        tokenizer.added_tokens_decoder = {v: k for k, v in tokenizer.added_tokens_encoder.items()}

    elif model_size in ['40B']:
        tokenizer = LlamaTokenizer.from_pretrained(model_path)
        # TODO:
        tokenizer.added_tokens_encoder = {'<unk>': 0, '<|startoftext|>': 1, '<|endoftext|>': 2, '<|im_start|>': 6, '<|im_end|>': 7, '<img>': 68, '</img>': 70, '<IMG_CONTEXT>': 64000, '<quad>': 64001, '</quad>': 64002, '<ref>': 64003, '</ref>': 64004, '<box>': 64005, '</box>': 64006}
        tokenizer.added_tokens_decoder = {v: k for k, v in tokenizer.added_tokens_encoder.items()}

    elif model_size in ['76B']:
        tokenizer = Llama3Tokenizer.from_pretrained(model_path)
        # TODO:
        tokenizer.added_tokens_encoder = {'<img>': 128256, '</img>': 128257, '<IMG_CONTEXT>': 128258, '<quad>': 128259, '</quad>': 128260, '<ref>': 128261, '</ref>': 128262, '<box>': 128263, '</box>': 128264}
        tokenizer.added_tokens_decoder = {v: k for k, v in tokenizer.added_tokens_encoder.items()}

    else:
        raise ValueError

    return tokenizer


def main(args):
    if args.image_path is not None and args.image_path != 'None':
        pixel_values = load_image(args.image_path, max_num=12).to(paddle.bfloat16)
        args.text = '<image>\n' + args.text

    else:
        pixel_values = None

    # init model and tokenizer
    MODEL_PATH = args.model_name_or_path
    model_size = MODEL_PATH.split('-')[-1]
    print(f'model size: {model_size}')
    tokenizer = load_tokenizer(model_size, MODEL_PATH)
    print('tokenizer:\n', tokenizer)
    print('len(tokenizer): ', len(tokenizer))

    model = InternVLChatModel.from_pretrained(MODEL_PATH).eval()

    generation_config = dict(max_new_tokens=1024, do_sample=False)

    with paddle.no_grad():
        response, history = model.chat(tokenizer, pixel_values, args.text, generation_config, history=None, return_history=True)
        print(f'User: {args.text}\nAssistant: {response}')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model_name_or_path",
        type=str,
        default="OpenGVLab/InternVL2-8B",
        help="pretrained ckpt and tokenizer",
    )
    parser.add_argument("--image_path", type=str, default=None)
    parser.add_argument("--text", type=str, default='Please describe the image shortly.', required=True)
    args = parser.parse_args()
    main(args)