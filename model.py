# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/Assignment_15_ERA/transformers.ipynb.

# %% auto 0
__all__ = ['LayerNormalization', 'FeedForwardBlock', 'InputEmbeddings', 'PositionEncoding', 'ResidualConnection',
           'MultiHeadAttentionBlock', 'EncoderBlock', 'Encoder', 'DecoderBlock', 'Decoder', 'ProjectionLayer',
           'Transformer', 'build_transformer']

# %% ../nbs/Assignment_15_ERA/transformers.ipynb 2
import torch
import torch.nn as nn
import math

# %% ../nbs/Assignment_15_ERA/transformers.ipynb 3
class LayerNormalization(nn.Module):
    def __init__(self,eps:float = 10**-6) -> None:
        super().__init__()
        self.eps = eps
        self.alpha = nn.Parameter(torch.ones(1)) #alpha is a learnable parameter
        self.bias = nn.Parameter(torch.zeros(1)) #bias is a learnable parameter
        
    def  forward(self,x):
        mean = x.mean(dim= -1,keepdim = True)
        std = x.std(dim = -1,keepdim = True)
        return self.alpha * (x-mean) /(std + self.eps) + self.bias

# %% ../nbs/Assignment_15_ERA/transformers.ipynb 6
class FeedForwardBlock(nn.Module):
    def __init__(self,d_model:int,d_ff:int,dropout:float) -> None:
        super().__init__()
        self.linear_1 = nn.Linear(d_model,d_ff)
        self.dropout = nn.Dropout(dropout)
        self.linear_2 = nn.Linear(d_ff,d_model)

    def forward(self,x):
        return self.linear_2(self.dropout(torch.relu(self.linear_1(x))))

# %% ../nbs/Assignment_15_ERA/transformers.ipynb 10
class InputEmbeddings(nn.Module):
    def __init__(self,vocab_size:int,d_model:int) -> None:
        super().__init__()
        self.d_model = d_model
        self.vocab_size = vocab_size
        self.embedding = nn.Embedding(vocab_size,d_model)

    def forward(self,x):
        return self.embedding(x) * math.sqrt(self.d_model)

# %% ../nbs/Assignment_15_ERA/transformers.ipynb 28
class PositionEncoding(nn.Module):
    def __init__(self,d_model:int,seq_len:int,dropout:float) -> None:
        super().__init__()
        self.d_model = d_model
        self.seq_len = seq_len
        self.dropout = nn.Dropout(dropout)
        pe = torch.zeros(seq_len,d_model)
        position = torch.arange(0,seq_len,dtype = torch.float).unsqueeze(1) # (seq_len,1)
        div_term = torch.exp(torch.arange(0,d_model,2).float() * (-math.log(10000.0)/d_model))
        pe[:,0::2] = torch.sin(position * div_term)
        pe[:,1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)
        self.register_buffer('pe',pe)


    def forward(self,x):
        x = x + (self.pe[:,:x.shape[1],:]).requires_grad_(False)
        return self.dropout(x)
    
        

# %% ../nbs/Assignment_15_ERA/transformers.ipynb 31
class ResidualConnection(nn.Module):
    def __init__(self,dropout:float) -> None:
        super().__init__()
        self.dropout = nn.Dropout(dropout)
        self.norm = LayerNormalization()

    def forward(self,x,sublayer):
        return x + self.dropout(sublayer(self.norm(x)))
        

# %% ../nbs/Assignment_15_ERA/transformers.ipynb 33
class MultiHeadAttentionBlock(nn.Module):
    def __init__(self,d_model:int,h:int,dropout:float) -> None:
        super().__init__()
        self.d_model = d_model
        self.h = h
        assert d_model % h == 0, "d_model is not divisible by h"
        self.d_k = d_model // h
        self.w_q = nn.Linear(d_model,d_model,bias=False)
        self.w_k = nn.Linear(d_model,d_model,bias=False)
        self.w_v = nn.Linear(d_model,d_model,bias=False)
        self.w_o = nn.Linear(d_model,d_model,bias=False)
        self.dropout = nn.Dropout(dropout)

    @staticmethod
    def attention(query, key ,value,mask,dropout:nn.Dropout):
        d_k = query.shape[-1]
        #see the transformed shapes
        attention_scores = (query @ key.transpose(-2,-1)) / math.sqrt(d_k)
        if mask is not None:
            attention_scores.masked_fill_(mask == 0 ,-1e9)
        attention_scores = attention_scores.softmax(dim = -1)
        if dropout is not None:
            attention_scores = dropout(attention_scores)  
        return (attention_scores @ value), attention_scores


    def forward(self, q, k, v, mask) :
        query = self.w_q(q)
        key  = self.w_k(k)
        value  = self.w_v(v)

        query = query.view(query.shape[0],query.shape[1],self.h,self.d_k).transpose(1,2)
        key = key.view(key.shape[0],key.shape[1],self.h,self.d_k).transpose(1,2)
        value = value.view(value.shape[0],value.shape[1],self.h,self.d_k).transpose(1,2)

        #calculating attention
        x, self.attention_scores = MultiHeadAttentionBlock.attention(query, key ,value,mask,self.dropout)

        #combining all the heads together
        x = x.transpose(1,2).contiguous().view(x.shape[0], -1, self.h * self.d_k)

        #pass through the projection layer
        return self.w_o(x)


        
        

# %% ../nbs/Assignment_15_ERA/transformers.ipynb 38
class EncoderBlock(nn.Module):
    def __init__(self,self_attention_block:MultiHeadAttentionBlock,feed_forward_block:FeedForwardBlock,dropout):
        super().__init__()
        self.self_attention_block = self_attention_block
        self.feed_forward_block = feed_forward_block
        self.residual_connections = nn.ModuleList([ ResidualConnection(dropout) for _ in range(2)])

    def forward(self,x,src_mask):
        x = self.residual_connections[0](x, lambda x : self.self_attention_block(x,x,x,src_mask))
        x = self.residual_connections[1](x, self.feed_forward_block)
        return x

# %% ../nbs/Assignment_15_ERA/transformers.ipynb 42
class Encoder(nn.Module):
    def __init__(self,layers:nn.ModuleList) -> None:
        super().__init__()
        self.layers = layers
        self.norm = LayerNormalization()

    def forward(self,x,mask):
        for layer in self.layers:
            x = layer(x,mask)
        return self.norm(x)

# %% ../nbs/Assignment_15_ERA/transformers.ipynb 44
class DecoderBlock(nn.Module):
    def __init__(self,self_attention_block:MultiHeadAttentionBlock,cross_attention_block:MultiHeadAttentionBlock,feed_forward_block:FeedForwardBlock,dropout):
        super().__init__()
        self.self_attention_block = self_attention_block
        self.cross_attention_block = cross_attention_block
        self.feed_forward_block = feed_forward_block
        self.residual_connections = nn.ModuleList([ ResidualConnection(dropout) for _ in range(3)])

    def forward(self,x,encoder_output,src_mask,tgt_mask):
        x = self.residual_connections[0](x, lambda x : self.self_attention_block(x,x,x,tgt_mask))
        x = self.residual_connections[1](x, lambda x : self.cross_attention_block(x,encoder_output,encoder_output,src_mask))
        x = self.residual_connections[2](x, self.feed_forward_block)
        return x

# %% ../nbs/Assignment_15_ERA/transformers.ipynb 48
class Decoder(nn.Module):
    def __init__(self,layers:nn.ModuleList) -> None:
        super().__init__()
        self.layers = layers
        self.norm = LayerNormalization()

    def forward(self,x,encoder_output,src_mask,tgt_mask):
        for layer in self.layers:
            x = layer(x,encoder_output,src_mask,tgt_mask)
        return self.norm(x)

# %% ../nbs/Assignment_15_ERA/transformers.ipynb 50
class ProjectionLayer(nn.Module):
    def __init__(self,d_model,vocab_size) -> None:
        super().__init__()
        self.proj = nn.Linear(d_model,vocab_size)

    def forward(self,x) -> None:
        return torch.softmax(self.proj(x), dim = -1)
    


# %% ../nbs/Assignment_15_ERA/transformers.ipynb 53
class Transformer(nn.Module):
    def __init__(self,encoder:Encoder,decoder:Decoder,src_embed:InputEmbeddings,tgt_embed:InputEmbeddings,src_pos,
                 tgt_pos,projection_layer:ProjectionLayer):
        super().__init__()
        self.encoder = encoder
        self.decoder = decoder
        self.src_embed = src_embed
        self.tgt_embed = tgt_embed
        self.src_pos = src_pos
        self.tgt_pos = tgt_pos
        self.projection_layer = projection_layer

    def encode(self,src,src_mask):
        src = self.src_embed(src)
        src = self.src_pos(src)
        return self.encoder(src,src_mask)

    def decode(self, encoder_output: torch.Tensor,src_mask:torch.Tensor,tgt:torch.Tensor,tgt_mask:torch.Tensor):
        tgt = self.tgt_embed(tgt)
        tgt = self.tgt_pos(tgt)
        return self.decoder(tgt,encoder_output,src_mask,tgt_mask)

    def project(self,x):
        return self.projection_layer(x)

    


                                         
            


        



        

# %% ../nbs/Assignment_15_ERA/transformers.ipynb 54
def build_transformer(src_vocab_size:int,tgt_vocab_size:int,src_seq_len:int,tgt_seq_len:int,d_model:int=512,
                          N:int=6,h:int=8,dropout:float=0.1,d_ff:int=2048) -> Transformer :

        #create the embeddings layer
        src_embed = InputEmbeddings(src_vocab_size,d_model)
        tgt_embed = InputEmbeddings(tgt_vocab_size,d_model)

        #create the positional encoding layers
        src_pos = PositionEncoding(d_model,src_seq_len,dropout)
        tgt_pos = PositionEncoding(d_model,tgt_seq_len,dropout)

        #create the encoder blocks
        encoder_blocks = []
        for _ in range(N):
            encoder_self_attention_block = MultiHeadAttentionBlock(d_model,h,dropout)
            feed_forward_block = FeedForwardBlock(d_model, d_ff, dropout)
            encoder_block = EncoderBlock(encoder_self_attention_block,feed_forward_block,dropout)
            encoder_blocks.append(encoder_block)

        #create the decoder blocks
        decoder_blocks = []
        for _ in range(N):
            decoder_self_attention_block = MultiHeadAttentionBlock(d_model,h,dropout)
            decoder_cross_attention_block = MultiHeadAttentionBlock(d_model,h,dropout)
            feed_forward_block = FeedForwardBlock(d_model, d_ff, dropout)
            decoder_block = DecoderBlock(decoder_self_attention_block,decoder_cross_attention_block,feed_forward_block,dropout)
            decoder_blocks.append(decoder_block)

        #create the encoder and decoder
        encoder = Encoder(nn.ModuleList(encoder_blocks))
        decoder = Decoder(nn.ModuleList(decoder_blocks))

        #create the projection layer
        projection_layer = ProjectionLayer(d_model,tgt_vocab_size)

        #create the transformer
        transformer = Transformer(encoder,decoder,src_embed,tgt_embed,src_pos,tgt_pos,projection_layer)

        #Initialise the parameters
        for p in transformer.parameters():
            if p.dim() > 1:
                nn.init.xavier_uniform_(p)

        return transformer
            
